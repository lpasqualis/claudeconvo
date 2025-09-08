# Changelog

All notable changes to claudeconvo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Watch mode (`-w`/`--watch`) for tailing session logs in real-time
- ESC key support to exit watch mode (in addition to Ctrl+C)
- Multiple color themes optimized for different terminal backgrounds
- Support for 8 built-in themes: dark, light, solarized-dark/light, dracula, nord, mono, high-contrast
- `--theme` command-line option to select color themes
- Environment variable `CLAUDECONVO_THEME` for setting default theme
- Configuration file support (`~/.claudeconvorc`) for persistent settings
- Ability to set default show options in config file

### Changed
- Refactored color system to use theme classes for better maintainability
- `--no-color` now acts as alias for `--theme mono`

### Fixed
- Tool truncation with `-st` option now correctly shows full tool output without truncation

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

[Unreleased]: https://github.com/lpasqualis/claudeconvo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lpasqualis/claudeconvo/releases/tag/v0.1.0
## [0.2.0] - 2025-09-08

### Changed
- **BREAKING**: Renamed project from `claudelog` to `claudeconvo`
  - Command changed from `claudelog` to `claudeconvo`
  - Package name changed from `claudelog` to `claudeconvo`
  - All imports must be updated to use `claudeconvo`
  - Environment variables changed from `CLAUDELOG_*` to `CLAUDECONVO_*`
- Updated all documentation to reflect new name
- GitHub repository will be renamed to match

### Migration
- Users should uninstall `claudelog` and install `claudeconvo` instead
- See docs/MIGRATION.md for detailed migration instructions
