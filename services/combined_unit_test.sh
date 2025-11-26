#!/bin/bash
set -e

SERVICES_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Running scraper_deployed tests ==="
cd "$SERVICES_DIR/scraper_deployed"
uv run python -m pytest test/ -v --cov=. --cov-report=
cp .coverage "$SERVICES_DIR/.coverage.scraper"

echo "=== Running loader_testing tests ==="
cd "$SERVICES_DIR/loader_testing"
DATABASE_URL="postgresql://test:test@localhost:5432/testdb" \
GOOGLE_CLOUD_PROJECT="test-project" \
uv run python -m pytest tests/unit/ -v --cov=api --cov-report=
cp .coverage "$SERVICES_DIR/.coverage.loader"

echo "=== Running chatter_deployed coverage (no tests) ==="
cd "$SERVICES_DIR/chatter_deployed"
uv run python -m coverage run --source=. -m pytest --collect-only 2>/dev/null || true
cp .coverage "$SERVICES_DIR/.coverage.chatter"

echo "=== Combining coverage reports ==="
cd "$SERVICES_DIR"
coverage combine .coverage.scraper .coverage.loader .coverage.chatter
coverage html

echo "=== Done! Opening report ==="
open htmlcov/index.html