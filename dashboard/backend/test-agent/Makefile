.PHONY: install install-dev test lint format run clean

install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

run:
	python src/main.py

clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
