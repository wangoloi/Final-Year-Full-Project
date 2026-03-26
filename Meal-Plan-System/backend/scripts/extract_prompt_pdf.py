"""
Extract text from Prompt.pdf into knowledge/clinical_prompt_supplement.txt.

  pip install pypdf
  python scripts/extract_prompt_pdf.py path/to/Prompt.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
_out = _backend / "knowledge" / "clinical_prompt_supplement.txt"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_prompt_pdf.py <path-to-Prompt.pdf>", file=sys.stderr)
        sys.exit(1)
    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.is_file():
        print(f"Not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    try:
        from pypdf import PdfReader
    except ImportError:
        print("Install pypdf: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    reader = PdfReader(str(pdf_path))
    parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        parts.append(t.strip())
    text = "\n\n".join(p for p in parts if p).strip()
    if not text:
        print("No text extracted (scanned PDF?); try manual copy/paste.", file=sys.stderr)
        sys.exit(1)
    _out.parent.mkdir(parents=True, exist_ok=True)
    _out.write_text(text, encoding="utf-8")
    print(f"Wrote {_out} ({len(text)} chars)")


if __name__ == "__main__":
    main()
