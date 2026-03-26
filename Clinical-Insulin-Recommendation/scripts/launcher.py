#!/usr/bin/env python3
"""
GlucoSense Launcher – start backend & frontend, open in browser, optional public tunnel.

Usage:
  python launcher.py                    # Start services, open default browser
  python launcher.py --browser chrome   # Open in Chrome
  python launcher.py --share            # Start services and print a public URL

Uses only stdlib: subprocess, argparse, webbrowser, socket, time.
Tunneling (--share) requires Node.js/npx and localtunnel.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import re
import shutil
import threading
import time
import webbrowser
from pathlib import Path

# -----------------------------------------------------------------------------
# Configuration – change ports/commands here
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# Backend: run from PROJECT_ROOT
BACKEND_CMD = [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT)]
BACKEND_CWD = PROJECT_ROOT

FRONTEND_CWD = FRONTEND_DIR
# Ports to check when detecting an already-running frontend instance.
FRONTEND_PORT_RANGE = range(FRONTEND_PORT, FRONTEND_PORT + 6)  # 5173..5178

# Timeouts (seconds)
BACKEND_START_TIMEOUT = 60
FRONTEND_START_TIMEOUT = 120
PORT_CHECK_INTERVAL = 0.5


def is_port_in_use(host: str, port: int) -> bool:
    """Return True if the port is reachable over IPv4 or IPv6."""
    hosts = [host]
    if host in {"127.0.0.1", "::1", "localhost"}:
        hosts = ["127.0.0.1", "::1", "localhost"]

    infos = []
    for candidate in hosts:
        try:
            infos.extend(socket.getaddrinfo(candidate, port, socket.AF_UNSPEC, socket.SOCK_STREAM))
        except socket.gaierror:
            continue
    if not infos:
        return False

    for family, socktype, proto, _, sockaddr in infos:
        try:
            with socket.socket(family, socktype, proto) as s:
                s.settimeout(1)
                s.connect(sockaddr)
                return True
        except (socket.error, OSError):
            continue
    return False


def wait_for_server(host: str, port: int, timeout: float, service_name: str) -> bool:
    """Poll until the server is reachable or timeout. Return True if ready."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_in_use(host, port):
            return True
        time.sleep(PORT_CHECK_INTERVAL)
    return False


def find_frontend_port() -> int | None:
    """Return the first port in FRONTEND_PORT_RANGE that has a server listening, or None."""
    for port in FRONTEND_PORT_RANGE:
        if is_port_in_use("127.0.0.1", port):
            return port
    return None


def _which_all(candidates: list[str]) -> str | None:
    """Return the first resolvable executable path from candidates."""
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def resolve_frontend_command() -> list[str] | None:
    """Resolve a frontend start command that works across Windows PATH variants."""
    vite_args = ["--port", str(FRONTEND_PORT), "--strictPort"]

    if sys.platform == "win32":
        npm_cmd = _which_all(["npm.cmd", "npm"])
        if npm_cmd:
            return [npm_cmd, "run", "dev", "--", *vite_args]

        local_vite_cmd = FRONTEND_DIR / "node_modules" / ".bin" / "vite.cmd"
        if local_vite_cmd.exists():
            return [str(local_vite_cmd), *vite_args]

        node_cmd = _which_all(["node.exe", "node"])
        vite_js = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
        if node_cmd and vite_js.exists():
            return [node_cmd, str(vite_js), *vite_args]
        return None

    npm_cmd = _which_all(["npm"])
    if npm_cmd:
        return [npm_cmd, "run", "dev", "--", *vite_args]

    local_vite = FRONTEND_DIR / "node_modules" / ".bin" / "vite"
    if local_vite.exists():
        return [str(local_vite), *vite_args]
    return None


def resolve_npx_command() -> list[str] | None:
    """Resolve npx command for localtunnel, handling Windows cmd wrappers."""
    if sys.platform == "win32":
        npx_cmd = _which_all(["npx.cmd", "npx"])
        return [npx_cmd] if npx_cmd else None
    npx_cmd = _which_all(["npx"])
    return [npx_cmd] if npx_cmd else None


def start_backend() -> subprocess.Popen | None:
    """Start the backend process. Returns the Popen instance or None on failure."""
    print("[launcher] Starting backend...")
    try:
        proc = subprocess.Popen(
            BACKEND_CMD,
            cwd=str(BACKEND_CWD),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        return proc
    except Exception as e:
        print(f"[launcher] Failed to start backend: {e}", file=sys.stderr)
        return None


def start_frontend() -> subprocess.Popen | None:
    """Start the frontend process. Returns Popen or None."""
    print("[launcher] Starting frontend...")
    frontend_cmd = resolve_frontend_command()
    if not frontend_cmd:
        print(
            "[launcher] Could not find npm/vite runner. Install Node.js and run "
            "'cd frontend && npm install'.",
            file=sys.stderr,
        )
        return None
    try:
        proc = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_CWD),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        return proc
    except FileNotFoundError:
        print("[launcher] npm not found on PATH.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[launcher] Failed to start frontend: {e}", file=sys.stderr)
        return None


def extract_vite_port(line: str) -> int | None:
    """
    Parse a Vite output line and return the localhost port if present.
    Example line: "Local:   http://localhost:5173/"
    """
    match = re.search(r"http://(?:localhost|127\.0\.0\.1):(\d+)", line)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def wait_for_frontend(frontend_proc: subprocess.Popen, timeout: float) -> int | None:
    """
    Wait for frontend readiness and return the resolved frontend port.
    Reads Vite output incrementally to avoid pipe backpressure and to discover
    the actual port quickly.
    """
    print("[launcher] Waiting for frontend to become ready...")
    deadline = time.monotonic() + timeout
    output_tail: list[str] = []

    while time.monotonic() < deadline:
        if frontend_proc.poll() is not None:
            break

        # If Vite reports URL, use that immediately.
        if frontend_proc.stdout:
            line = frontend_proc.stdout.readline()
            if line:
                text = line.rstrip()
                output_tail.append(text)
                if len(output_tail) > 30:
                    output_tail.pop(0)

                port = extract_vite_port(text)
                if port is not None and is_port_in_use("127.0.0.1", port):
                    return port

        # Fallback check in case output is delayed or format changes.
        detected = find_frontend_port()
        if detected is not None:
            return detected

        time.sleep(PORT_CHECK_INTERVAL)

    if frontend_proc.stdout:
        try:
            remaining = frontend_proc.stdout.read()
            if remaining:
                output_tail.extend(remaining.strip().splitlines())
        except Exception:
            pass

    if output_tail:
        print("[launcher] Last frontend output:", file=sys.stderr)
        for line in output_tail[-15:]:
            print(f"  {line}", file=sys.stderr)
    return None


def open_browser(url: str, browser_name: str | None) -> None:
    """Open url in the specified browser or the system default."""
    try:
        if browser_name:
            try:
                controller = webbrowser.get(browser_name)
                controller.open(url)
                print(f"[launcher] Opened {url} in {browser_name}.")
            except webbrowser.Error:
                print(f"[launcher] Browser '{browser_name}' not found, using default.", file=sys.stderr)
                webbrowser.open(url)
                print(f"[launcher] Opened {url} in default browser.")
        else:
            webbrowser.open(url)
            print(f"[launcher] Opened {url} in default browser.")
    except Exception as e:
        print(f"[launcher] Could not open browser: {e}", file=sys.stderr)
        print(f"[launcher] Open manually: {url}")


def run_tunnel(port: int) -> str | None:
    """
    Run localtunnel (npx localtunnel --port PORT), capture the public URL from
    output, and leave the tunnel process running.
    Returns the URL or None if tunnel failed or npx is not available.
    """
    print("[launcher] Starting tunnel (npx localtunnel)...")
    captured_url: list[str] = []
    npx_cmd = resolve_npx_command()
    if not npx_cmd:
        print("[launcher] npx not found. Install Node.js for --share.", file=sys.stderr)
        return None

    def read_output(stream):
        try:
            for line in iter(stream.readline, ""):
                line = line.strip()
                if "http" in line.lower() and "localhost" not in line:
                    for part in line.split():
                        if part.startswith("http"):
                            captured_url.append(part.rstrip(".,;:"))
                            return
        except Exception:
            pass

    try:
        proc = subprocess.Popen(
            [*npx_cmd, "--yes", "localtunnel", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        reader = threading.Thread(target=read_output, args=(proc.stdout,), daemon=True)
        reader.start()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if captured_url:
                print("[launcher] Tunnel is running. Share this URL (keep launcher running).")
                return captured_url[0]
            if proc.poll() is not None:
                break
            time.sleep(0.3)
        if not captured_url and proc.poll() is not None and proc.returncode != 0:
            print("[launcher] Tunnel process exited with an error.", file=sys.stderr)
        return captured_url[0] if captured_url else None
    except FileNotFoundError:
        print("[launcher] npx not found. Install Node.js for --share.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[launcher] Tunnel error: {e}", file=sys.stderr)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Start GlucoSense backend & frontend, open in browser, optional public URL."
    )
    parser.add_argument(
        "--browser",
        metavar="NAME",
        default=None,
        help="Browser to use (e.g. chrome, firefox). Default: system default.",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Start a public tunnel and print the shareable URL.",
    )
    args = parser.parse_args()

    frontend_port_used = FRONTEND_PORT
    app_url = f"http://localhost:{FRONTEND_PORT}"

    # Start backend first so API is available regardless of frontend state.
    if is_port_in_use("127.0.0.1", BACKEND_PORT):
        print("[launcher] Backend already running on port {} (skipping start).".format(BACKEND_PORT))
    else:
        backend_proc = start_backend()
        if backend_proc is None:
            print("[launcher] Could not start backend. Check that Python and uvicorn are available.", file=sys.stderr)
            return 1
        if not wait_for_server("127.0.0.1", BACKEND_PORT, BACKEND_START_TIMEOUT, "backend"):
            print("[launcher] Backend did not become ready in time.", file=sys.stderr)
            print("[launcher] If port {} is in use, stop that process or run: uvicorn app:app --port 8001".format(BACKEND_PORT), file=sys.stderr)
            backend_proc.terminate()
            return 1
        print("[launcher] Backend ready on port {}.".format(BACKEND_PORT))

    # If frontend is already up on any usual port (5173–5178), use it
    existing = find_frontend_port()
    if existing is not None:
        frontend_port_used = existing
        app_url = f"http://localhost:{existing}"
        print(f"[launcher] Frontend already running (port {existing}).")
    else:
        # Start frontend on fixed port (FRONTEND_PORT)
        frontend_proc = start_frontend()
        if frontend_proc is None:
            return 1
        detected_port = wait_for_frontend(frontend_proc, FRONTEND_START_TIMEOUT)
        if detected_port is None:
            print("[launcher] Frontend did not become ready in time.", file=sys.stderr)
            frontend_proc.terminate()
            return 1
        frontend_port_used = detected_port
        app_url = f"http://localhost:{detected_port}"
        print(f"[launcher] Frontend ready on port {detected_port}.")

    print(f"[launcher] App URL: {app_url}")

    if not args.share:
        open_browser(app_url, args.browser)
        return 0

    public_url = run_tunnel(frontend_port_used)
    if public_url:
        print(f"[launcher] Public URL: {public_url}")
        open_browser(app_url, args.browser)
    else:
        print("[launcher] Could not create public URL. Open locally:", app_url, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
