.PHONY: install install-dev test lint type-check format build clean docs help

# ── Variables ──────────────────────────────────────────────────────────────
PYTHON      := python
PIP         := $(PYTHON) -m pip
SDK_SRC     := sdk/python/agentability
TEST_SRC    := sdk/python/tests

# ── Help ───────────────────────────────────────────────────────────────────
help:
	@echo "Available targets:"
	@echo "  install       Install the package (editable)"
	@echo "  install-dev   Install with all dev dependencies"
	@echo "  test          Run the test suite with coverage"
	@echo "  lint          Run ruff + flake8 linters"
	@echo "  type-check    Run mypy static type checking"
	@echo "  format        Apply black + isort formatting"
	@echo "  build         Build wheel and sdist"
	@echo "  clean         Remove build artefacts"
	@echo "  docs          Build the Sphinx / Docusaurus docs"

# ── Installation ───────────────────────────────────────────────────────────
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev,all-integrations,all-storage]"
	pre-commit install

# ── Quality ────────────────────────────────────────────────────────────────
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

# ── Build ──────────────────────────────────────────────────────────────────
build:
	$(PYTHON) -m build

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.py[cod]" -delete

# ── Documentation ──────────────────────────────────────────────────────────
docs:
	@echo "See docs/ directory for Docusaurus source."
