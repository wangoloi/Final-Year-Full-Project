#!/usr/bin/env bash
# Meal-Plan-System — local CI (pytest + frontend build)
# Run from Meal-Plan-System/:  chmod +x scripts/ci.sh && ./scripts/ci.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Meal-Plan-System CI ==="

echo ""
echo "[1/2] Backend: pytest..."
python -m pytest backend/tests -q

echo ""
echo "[2/2] Frontend: npm ci + build..."
cd frontend
npm ci
npm run build

echo ""
echo "OK — same checks as .github/workflows/meal-plan-ci.yml"
