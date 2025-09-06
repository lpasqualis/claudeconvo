# Changelog

All notable changes to claudelog will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multiple color themes optimized for different terminal backgrounds
- Support for 8 built-in themes: dark, light, solarized-dark/light, dracula, nord, mono, high-contrast
- `--theme` command-line option to select color themes
- Environment variable `CLAUDELOG_THEME` for setting default theme
- Configuration file support (`~/.claudelogrc`) for persistent settings
- Ability to set default show options in config file

### Changed
- Refactored color system to use theme classes for better maintainability
- `--no-color` now acts as alias for `--theme mono`

## [0.1.0] - 2025-01-XX

### Added
- Initial release of claudelog
- View Claude Code session history as formatted conversations
- Colored output for different message types
- Filtering options for message types
- Support for relative and absolute session references
- Rich formatting with indentation and line wrapping
- Command-line interface with multiple options
- Homebrew formula support
- PyPI package distribution

### Features
- Display user and assistant messages
- Show/hide tool executions
- Show/hide system messages and metadata
- Session listing and selection
- Configurable display options via command-line flags

[Unreleased]: https://github.com/lpasqualis/claudelog/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lpasqualis/claudelog/releases/tag/v0.1.0