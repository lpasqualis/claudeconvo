# claudelog

View Claude Code session history as a conversation

`claudelog` is a command-line utility that loads and displays Claude Code session files stored in `~/.claude/projects/` for the current working directory, formatted as readable conversations with colored output for different speakers and tool executions.

## Features

- Display Claude Code conversations with colored, formatted output
- Multiple color themes optimized for different terminal backgrounds
- Filter messages by type (user, assistant, tools, system, etc.)
- Show or hide metadata, tool details, and system messages
- Support for relative and absolute session references
- Rich formatting with proper indentation and line wrapping
- Configuration file support for persistent settings

## Installation

### Using pip

```bash
pip install claudelog
```

### Using Homebrew (macOS/Linux)

```bash
brew tap lpasqualis/tap
brew install claudelog
```

### From source

```bash
git clone https://github.com/lpasqualis/claudelog.git
cd claudelog
pip install -e .
```

## Usage

### Basic Usage

```bash
# View the most recent session
claudelog

# View a specific session by number
claudelog 3

# View previous session
claudelog -1
```

### Filtering Options

Use single-letter flags to control what content is displayed:

```bash
# Show only user and assistant messages (default)
claudelog

# Show all content
claudelog -a

# Show summaries and metadata
claudelog -sm

# Show tool executions with full details
claudelog -ot
```

#### Available Options

- `q` - Show user messages
- `w` - Show assistant (Claude) messages
- `s` - Show session summaries
- `h` - Show hook executions
- `m` - Show metadata (uuid, sessionId, version, etc.)
- `c` - Show command-related messages
- `y` - Show all system messages
- `t` - Show full tool details without truncation
- `o` - Show tool executions
- `e` - Show all error details and warnings
- `r` - Show API request IDs
- `f` - Show parent/child relationships
- `u` - Show all content without truncation
- `d` - Show performance metrics and token counts
- `p` - Show working directory (cwd) for each message
- `l` - Show message level/priority
- `k` - Show sidechain/parallel messages
- `v` - Show user type for each message
- `a` - Enable all options

Uppercase letters disable options:
- `aH` - Enable all except hooks
- `Aqw` - Disable all, then enable only user and assistant messages

### Color Themes

Choose from multiple color themes optimized for different terminal backgrounds:

```bash
# Use light theme for white/light terminals
claudelog --theme light

# Use high contrast theme for accessibility
claudelog --theme high-contrast

# Disable colors entirely
claudelog --no-color
```

Available themes:
- `dark` (default) - Optimized for dark terminal backgrounds
- `light` - Optimized for light/white terminal backgrounds  
- `solarized-dark` - Solarized dark color scheme
- `solarized-light` - Solarized light color scheme
- `dracula` - Dracula color scheme
- `nord` - Nord color scheme
- `mono` - No colors (monochrome)
- `high-contrast` - Maximum contrast for accessibility

Set a default theme using:
- Environment variable: `export CLAUDELOG_THEME=light`
- Config file: Create `~/.claudelogrc` with `{"theme": "light"}`

### Configuration

Create a `~/.claudelogrc` file to set persistent preferences:

```json
{
  "theme": "light",
  "default_show_options": "qwo"
}
```

Configuration priority (highest to lowest):
1. Command-line arguments
2. Environment variables
3. Config file (`~/.claudelogrc`)
4. Built-in defaults

### Help and Available Sessions

```bash
# Show help
claudelog --help

# List available sessions
claudelog --list

# Show what options would display
claudelog -?sm
```

## Requirements

- Python 3.8 or higher
- No external dependencies

## Development

### Setting up development environment

```bash
git clone https://github.com/lpasqualis/claudelog.git
cd claudelog
pip install -e ".[dev]"
```

### Running tests

```bash
pytest
```

### Code formatting and linting

```bash
black src/
ruff check src/
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Lorenzo Pasqualis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

If you encounter any problems or have suggestions, please [open an issue](https://github.com/lpasqualis/claudelog/issues).