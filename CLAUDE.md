# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MUST FOLLOW RULES
- Keep it SIMPLE, no speculative engineering and functionality
- Keep it DRY, no repetitions in the code, no hacks
- No hardcoded hacks made to pass test
- Remember this is a utility that needs to run in a multitude of environments. Don't make assumptions.
- This project is distributed as an opensource on GitHub, as a python package, and on Homebrew, so make sure everything you do is compatible with that and follows best practices
- Keep modules small and focused on a specific thing, no monolithic Python files
- Keep it clean, don't accumulate temporary junk
- Test it! All functionality must have unit tests, and tests must pass
- Claude log files format WILL CHANGE, the command needs to be able to have proper error handling and make it easy to adapt to changes
- It should be possible to run claudelog from any subfolder of a project, and the correct project should be identified automatically
- User experience using the CLI must be IMPECCABLE, and follow best practices for outstanding CLI experiences
- Warnings are not acceptable, ANYWHERE. Fix all warnings you receive from any tool or test

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

# Clean all build artifacts
# Lint and type check
make lint

# Format code (auto-fixes)
make format

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
3. **Color Output**: Direct ANSI codes in Colors class, can be disabled with --no-color and customized with themes
4. **Session Discovery**: Automatically finds sessions for current working directory, including subfolders of the project

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