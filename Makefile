.PHONY: help install install-dev test lint format clean build upload check-release

help:
	@echo "Available commands:"
	@echo "  make install       Install the package in production mode"
	@echo "  make install-dev   Install the package in development mode with dev dependencies"
	@echo "  make test          Run tests with coverage"
	@echo "  make lint          Run linting checks (ruff and mypy)"
	@echo "  make format        Format code with black"
	@echo "  make clean         Remove build artifacts and cache files"
	@echo "  make build         Build distribution packages"
	@echo "  make check-release Check if package is ready for release"
	@echo "  make upload        Upload to PyPI (requires credentials)"

install:
	pip3 install -e .

install-dev:
	pip3 install -e ".[dev]"

test:
	pytest tests/ -v --cov=src/claudelog --cov-report=term-missing

lint:
	ruff check src/
	mypy src/

format:
	black src/ tests/
	ruff check src/ --fix

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/

build: clean
	python -m build

check-release: build
	python3 -m twine check dist/*

upload: check-release
	@echo "Uploading to PyPI..."
	@echo "Make sure you have configured your PyPI credentials!"
	python3 -m twine upload dist/*