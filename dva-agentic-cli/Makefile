.PHONY: help install install-dev test test-cov lint format clean run

help:
	@echo "DVA Agentic CLI - Available commands:"
	@echo "  make install      - Install the package using uv"
	@echo "  make install-dev  - Install package with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code with ruff"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make run          - Run the CLI (example: make run ARGS='--version')"
	@echo "  make integration  - Run integration tests"

install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=dva_agentic_cli --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	dva $(ARGS)

# Integration tests
integration: install
	@echo "Running integration tests..."
	@echo "\n=== Testing version command ==="
	dva --version
	@echo "\n=== Testing help command ==="
	dva --help
	@echo "\n=== Testing hello command ==="
	dva hello
	dva hello "DVA Team"
	@echo "\n=== All integration tests passed! ==="
