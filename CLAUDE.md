# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`claudelog` is a command-line utility that displays Claude Code session history stored in `~/.claude/projects/` as readable, colored conversations. It has no external dependencies and works with Python 3.8+.

## Development Setup

The project requires a virtual environment due to system Python restrictions:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with development dependencies
make install-dev
```

## Common Development Commands

```bash
# Run tests with coverage
make test

# Run specific test
pytest tests/test_claudelog.py::TestShowOptions::test_default_options -v

# Lint and type check
make lint

# Format code (auto-fixes)
make format

# Clean all build artifacts
make clean

# Build distribution packages
make build

# Check if package is ready for release
make check-release
```

## Code Architecture

### Core Components

**ShowOptions** (`src/claudelog/claudelog.py:41-189`)
- Manages display filtering via single-letter flags (q=user, w=assistant, o=tools, etc.)
- Implements complex parsing logic: lowercase enables, uppercase disables, 'a'=all, 'A'=none
- Default shows user, assistant, and tools only

**SessionManager** (`src/claudelog/claudelog.py:201-280`)
- Handles session file discovery in `~/.claude/projects/`
- Maps working directories to session storage using path_to_session_dir()
- Supports relative/absolute session references

**MessageFormatter** (`src/claudelog/claudelog.py:282-580`)
- Renders messages with ANSI colors based on ShowOptions
- Handles tool executions, system messages, metadata
- Implements smart truncation and text wrapping

### Key Design Patterns

1. **No External Dependencies**: Pure Python stdlib only - critical for wide compatibility
2. **Option Parsing**: Custom flag system instead of argparse for show options to allow compact multi-flag syntax like `-saH`
3. **Color Output**: Direct ANSI codes in Colors class, can be disabled with --no-color
4. **Session Discovery**: Automatically finds sessions for current working directory

## Testing Strategy

Tests use mocking extensively to avoid filesystem dependencies:
- Mock Path.exists() and Path.iterdir() for session discovery
- Mock file reads for session data
- Test all ShowOptions combinations and edge cases

## Release Process

1. Update version in `pyproject.toml` and `src/claudelog/__init__.py`
2. Update CHANGELOG.md
3. Create and push tag: `git tag v0.1.0 && git push --tags`
4. GitHub Actions handles PyPI release (requires PYPI_API_TOKEN secret)
5. Update Homebrew formula following `homebrew-tap-instructions.md`

## Code Style Requirements

- Line length: 100 characters max
- Black formatting (enforced)
- Ruff linting with E, F, I, N, W, UP rules
- MyPy strict type checking (all untyped defs disallowed)
- Tests must maintain coverage

## Project-Specific Considerations

- The main script `claudelog.py` is intentionally a single file for simplicity
- Color codes are optimized for dark terminals (may need adjustment for light themes)
- Session file format is Claude Code's internal JSON structure - handle missing fields gracefully
- Tool output truncation is context-aware (different limits for params vs results)