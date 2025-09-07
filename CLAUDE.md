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
- Never put imports in the middle of the code, all the imports should be at the top

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

**ShowOptions** (`src/claudelog/options.py`)
- Manages display filtering via single-letter flags (q=user, w=assistant, o=tools, etc.)
- Implements complex parsing logic: lowercase enables, uppercase disables, 'a'=all, 'A'=none
- Default shows user, assistant, and tools only

**Session Management** (`src/claudelog/session.py`)
- Handles session file discovery in `~/.claude/projects/`
- Maps working directories to session storage using path_to_session_dir()
- Integrates with adaptive parser for format normalization
- Supports relative/absolute session references

**Message Formatting** (`src/claudelog/formatters.py`)
- Renders messages with ANSI colors based on ShowOptions
- Handles tool executions, system messages, metadata
- Implements smart truncation and text wrapping
- Uses adaptive parser for content extraction

**Color Themes** (`src/claudelog/themes.py`)
- 8 built-in themes: dark, light, solarized-dark/light, dracula, nord, mono, high-contrast
- Inheritance-based theme system to avoid repetition
- Runtime theme switching via proxy pattern
- Configurable via CLI, environment variable, or config file

**Adaptive Parser** (`src/claudelog/parsers/adaptive.py`)
- Detects and normalizes different Claude log format versions
- Handles format variations between Claude versions
- Extensible parser system for future format changes
- Configured via parsers.yaml with format specifications

### Key Design Patterns

1. **No External Dependencies**: Pure Python stdlib only - critical for wide compatibility
2. **Option Parsing**: Custom flag system instead of argparse for show options to allow compact multi-flag syntax like `-saH`
3. **Color Output**: Direct ANSI codes in Colors class, can be disabled with --no-color and customized with themes
4. **Session Discovery**: Automatically finds sessions for current working directory, including subfolders of the project

## Testing Strategy

### Test Structure
- Tests are organized by functional area in `tests/test_claudelog.py`
- Each major component has its own test class (TestShowOptions, TestMessageFormatting, TestSessionFunctions, etc.)
- Coverage target: maintain high coverage for critical parsing and formatting logic

### Mocking Approach
Tests use mocking to avoid filesystem and external dependencies:
- Mock `Path.exists()`, `Path.glob()`, and `Path.iterdir()` for session discovery
- Mock file reads with realistic Claude log format entries
- Mock parser configurations when testing adaptive parsing
- Use dependency injection for testable components

### Key Test Areas
1. **ShowOptions**: Test all flag combinations, uppercase/lowercase behavior, defaults
2. **Message Formatting**: Verify correct handling of user/assistant/tool messages
3. **Color Themes**: Ensure theme inheritance and proper ANSI code generation
4. **Session Parsing**: Handle various log format variations from different Claude versions
5. **Adaptive Parser**: Test format detection and normalization across versions
6. **Edge Cases**: Empty files, malformed JSON, missing fields, parse errors

### Test Data
- Use realistic Claude session data structures (with version fields, proper type structure)
- Test data should reflect actual log format variations found in production
- Include both legacy and current format examples

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