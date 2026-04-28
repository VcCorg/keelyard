.PHONY: help install install-dev test test-cov lint format clean run shell notebook

help:
	@echo "ADK Agent Project - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run linting checks"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make run          - Run the main application"
	@echo "  make shell        - Start IPython shell"
	@echo "  make notebook     - Start Jupyter notebook"

install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

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
	rm -rf logs/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python src/main.py

shell:
	ipython -i -c "from src.config import settings; from src.agents.example import ExampleAgent; print('Agent environment loaded. Try: agent = ExampleAgent()')"

notebook:
	jupyter notebook notebooks/
