# Contributing to claudelog

Thank you for your interest in contributing to claudelog! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions.

## How to Contribute

### Reporting Issues

1. Check if the issue already exists in the [issue tracker](https://github.com/lpasqualis/claudelog/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce (if applicable)
   - Expected vs actual behavior
   - System information (OS, Python version)

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Set up development environment:
   ```bash
   pip install -e ".[dev]"
   ```

4. Make your changes:
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

5. Run tests and checks:
   ```bash
   make lint
   make format
   make test
   ```

6. Commit with descriptive message:
   ```bash
   git commit -m "feat: add new feature description"
   ```

   Use conventional commits:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test additions/changes
   - `refactor:` Code refactoring
   - `style:` Formatting changes
   - `chore:` Maintenance tasks

7. Push and create pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

### Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/claudelog.git
   cd claudelog
   ```

2. Install in development mode:
   ```bash
   make install-dev
   ```

3. Run tests:
   ```bash
   make test
   ```

### Code Style

- Follow PEP 8
- Use black for formatting
- Use ruff for linting
- Add type hints where possible
- Maximum line length: 100 characters

### Testing

- Write tests for all new functionality
- Maintain or improve code coverage
- Tests should be in `tests/` directory
- Use pytest for testing

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions/classes
- Update inline comments for complex logic

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml` and `src/claudelog/__init__.py`
2. Update CHANGELOG.md
3. Create git tag: `git tag -a v0.1.0 -m "Release version 0.1.0"`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will handle PyPI release

## Questions?

Feel free to open an issue for any questions about contributing!