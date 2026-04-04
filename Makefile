.PHONY: install install-dev test lint type-check format build clean docs help \
        api api-install dashboard dashboard-install dev

# ── Variables ──────────────────────────────────────────────────────────────
PYTHON      := python
PIP         := $(PYTHON) -m pip
SDK_SRC     := sdk/python/agentability
TEST_SRC    := sdk/python/tests
API_SRC     := platform/api

# ── Help ───────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Agentability — Build Targets"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  SDK"
	@echo "    install       Install the SDK (editable)"
	@echo "    install-dev   Install SDK + all dev dependencies"
	@echo "    test          Run test suite (coverage >= 85%)"
	@echo "    lint          ruff + flake8"
	@echo "    type-check    mypy strict"
	@echo "    format        black + isort"
	@echo "    build         Build wheel + sdist"
	@echo ""
	@echo "  Platform"
	@echo "    api-install   Install FastAPI platform deps"
	@echo "    api           Start API server on :8000 (reload)"
	@echo ""
	@echo "  Dashboard"
	@echo "    dashboard-install  npm install dashboard deps"
	@echo "    dashboard          Start Vite dev server on :3000"
	@echo ""
	@echo "  Combined"
	@echo "    dev           Start API + dashboard concurrently"
	@echo "    clean         Remove all build artefacts"
	@echo ""

# ── SDK Installation ───────────────────────────────────────────────────────
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev,all-integrations,all-storage]"
	pre-commit install

# ── SDK Quality ────────────────────────────────────────────────────────────
test:
	pytest --cov=$(SDK_SRC) --cov-report=term-missing --cov-report=html -v

lint:
	ruff check $(SDK_SRC)
	flake8 $(SDK_SRC)

type-check:
	mypy $(SDK_SRC)

format:
	black $(SDK_SRC) $(TEST_SRC)
	isort $(SDK_SRC) $(TEST_SRC)

# ── SDK Build ──────────────────────────────────────────────────────────────
build:
	$(PYTHON) -m build

# ── Platform API ───────────────────────────────────────────────────────────
api-install:
	$(PIP) install -r platform/requirements.txt --break-system-packages 2>/dev/null || \
	$(PIP) install -r platform/requirements.txt

api:
	@echo "Starting Agentability API on http://localhost:8000 ..."
	@echo "Docs: http://localhost:8000/docs"
	AGENTABILITY_DB=${AGENTABILITY_DB:-agentability.db} \
	uvicorn platform.api.main:app --host 0.0.0.0 --port 8000 --reload

# ── Dashboard ──────────────────────────────────────────────────────────────
dashboard-install:
	cd dashboard && npm install

dashboard:
	@echo "Starting Agentability Dashboard on http://localhost:3000 ..."
	cd dashboard && npm run dev

# ── Combined dev (requires GNU make + background jobs) ────────────────────
dev:
	@echo "Starting API + Dashboard concurrently..."
	@echo "API  → http://localhost:8000/docs"
	@echo "UI   → http://localhost:3000"
	$(MAKE) api & $(MAKE) dashboard

# ── Clean ──────────────────────────────────────────────────────────────────
clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	rm -rf dashboard/dist dashboard/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.py[cod]" -delete

# ── Docs ───────────────────────────────────────────────────────────────────
docs:
	@echo "See docs/ directory for Docusaurus source."
