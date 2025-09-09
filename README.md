# claudeconvo

View Claude Code session history as a conversation

`claudeconvo` is a command-line utility that loads and displays Claude Code session files stored in `~/.claude/projects/` for the current working directory, formatted as readable conversations with colored output for different speakers and tool executions.

## What's New

### Recent Updates
- **Interactive Setup Mode** - Visual configuration with live preview (`--setup`)
- **Improved Light Theme Support** - Fixed visibility issues for white terminals
- **Complete Message Type Support** - Now displays hooks, commands, errors, and performance metrics
- **Enhanced Menu Layout** - Two-column display options, side-by-side themes and styles
- **Keyboard Shortcuts** - Quick exit with `X`, view with `Enter`, reset with `/reset`
- **Performance Metrics** - Show request duration and token counts with `-d` flag
- **Better Truncation** - Smart truncation of tool outputs with `-u` flag for full content

## Features

- Display Claude Code conversations with colored, formatted output
- Multiple color themes optimized for different terminal backgrounds (fixed for white terminals)
- Multiple formatting styles (default, boxed, minimal, compact)
- Filter messages by type (user, assistant, tools, system, hooks, commands, errors, etc.)
- Show or hide metadata, tool details, performance metrics, and system messages
- Support for relative and absolute session references
- Rich formatting with proper indentation and automatic line wrapping
- Interactive setup mode for visual configuration (`--setup`)
- Configuration file support for persistent settings
- Save current settings as defaults with `--set-defaults`
- Reset to original defaults with `--reset-defaults`
- Watch mode for live session monitoring (`-w`)
- Display performance metrics including duration and token counts
- Show hook executions, slash commands, and error details
- Adaptive parser system for handling different Claude log format versions

## Installation

### Using pip

```bash
pip install claudeconvo
```

### From source

```bash
git clone https://github.com/lpasqualis/claudeconvo.git
cd claudeconvo
pip install -e .
```

## Usage

### Basic Usage

```bash
# View the most recent session
claudeconvo

# View a specific session by number
claudeconvo 3

# View previous session
claudeconvo -1

# Watch a session for new entries (tail mode)
claudeconvo -w

# Watch a specific session
claudeconvo -f session-123 -w

# View with specific theme and style
claudeconvo --theme light --style boxed

# View last 2 sessions
claudeconvo -n 2
```

### Message Types

`claudeconvo` can display various types of messages from Claude Code sessions:

- **User Messages** - Your input and questions
- **Assistant Messages** - Claude's responses
- **Tool Executions** - File reads, edits, searches, and other tool uses
- **System Messages** - Session auto-saves, checkpoints
- **Summaries** - Conversation summaries and context
- **Hook Executions** - Pre-commit, post-save, and other hooks
- **Slash Commands** - Commands like `/docs`, `/test`, etc.
- **Errors and Warnings** - Error messages with detailed information
- **Performance Metrics** - Request duration and token usage

### Filtering Options

Use single-letter flags to control what content is displayed:

```bash
# Show default content (user, assistant, and tool executions)
claudeconvo

# Show all content including metadata, performance, errors
claudeconvo -a

# Show summaries and metadata
claudeconvo -sm

# Show tool executions with full details (no truncation)
claudeconvo -ot

# Show performance metrics and token counts
claudeconvo -d

# Show hooks, commands, and errors
claudeconvo -hce
```

#### Available Options

- `q` - Show user messages
- `w` - Show assistant (Claude) messages
- `s` - Show session summaries
- `h` - Show hook executions (pre-commit, post-save, etc.)
- `m` - Show metadata (uuid, sessionId, version, etc.)
- `c` - Show slash command executions (/docs, /test, etc.)
- `y` - Show all system messages (auto-save, checkpoints, etc.)
- `t` - Show full tool details without truncation
- `o` - Show tool executions
- `e` - Show all error details and warnings
- `r` - Show API request IDs
- `f` - Show parent/child relationships
- `u` - Show all content without truncation
- `d` - Show performance metrics (duration, tokens-in, tokens-out)
- `p` - Show working directory (cwd) for each message
- `l` - Show message level/priority
- `k` - Show sidechain/parallel messages
- `v` - Show user type for each message
- `i` - Show AI model name/version
- `a` - Enable all options
- `?` - Print what will be shown/hidden and exit

Uppercase letters disable options:
- `aH` - Enable all except hooks
- `Aqw` - Disable all, then enable only user and assistant messages

### Color Themes

Choose from multiple color themes optimized for different terminal backgrounds:

```bash
# Use light theme for white/light terminals
claudeconvo --theme light

# Use high contrast theme for accessibility
claudeconvo --theme high-contrast

# List all available themes
claudeconvo --theme

# Disable colors entirely
claudeconvo --no-color
```

Available themes:
- `dark` (default) - Optimized for dark terminal backgrounds
- `light` - Optimized for light/white terminal backgrounds (improved visibility)
- `solarized-dark` - Solarized dark color scheme
- `solarized-light` - Solarized light color scheme (improved for white backgrounds)
- `dracula` - Dracula color scheme
- `nord` - Nord color scheme
- `mono` - No colors (monochrome)
- `high-contrast` - Maximum contrast for accessibility

### Formatting Styles

Control how messages are displayed with different formatting styles:

```bash
# Use boxed style with borders around messages
claudeconvo --style boxed

# Use minimal style for clean, compact output
claudeconvo --style minimal

# Use compact style for condensed spacing
claudeconvo --style compact

# List all available styles
claudeconvo --style
```

Available styles:
- `default` - Standard formatting with clear labels
- `boxed` - Messages in boxes with borders
- `minimal` - Minimal decorations for clean output
- `compact` - Condensed spacing for more content

### Configuration

#### Interactive Setup

Use the interactive setup to visually configure your preferences:

```bash
# Launch interactive configuration
claudeconvo --setup

# Automated setup for testing (non-interactive)
claudeconvo --setup --ai "2 s2 t V /set"  # Light theme, boxed style, tool details, view, save
```

The interactive setup provides:
- Side-by-side theme and style selection
- Two-column layout for display options (enabled/disabled)
- Live preview of your configuration with sample messages
- Quick commands: `V` or `Enter` to view sample, `X` to quick exit
- `/set` to save as defaults, `/reset` to restore original defaults
- All 19 display options accessible with single-letter toggles
- Compact command-line format display of current settings

#### Setting Defaults

Save your current settings as defaults:

```bash
# Try out settings
claudeconvo --theme light --style boxed -w

# If you like them, save as defaults
claudeconvo --theme light --style boxed -w --set-defaults

# Reset to original defaults
claudeconvo --reset-defaults
```

#### Config File

Create a `~/.claudeconvorc` file to set persistent preferences:

```json
{
  "default_theme": "light",
  "default_style": "boxed",
  "default_show_options": "qwo",
  "default_watch": true
}
```

#### Configuration Priority

Settings are applied in this order (highest to lowest priority):
1. Command-line arguments
2. Environment variables (`CLAUDECONVO_THEME`)
3. Config file (`~/.claudeconvorc`)
4. Built-in defaults

### Help and Available Sessions

```bash
# Show help
claudeconvo --help

# List available sessions
claudeconvo --list

# Show current configuration
claudeconvo --show-config

# Check what options would display (quote to protect ? from shell)
claudeconvo '-saH?'
```

## Requirements

- Python 3.8 or higher
- No external dependencies

## Development

### Setting up development environment

```bash
git clone https://github.com/lpasqualis/claudeconvo.git
cd claudeconvo
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

If you encounter any problems or have suggestions, please [open an issue](https://github.com/lpasqualis/claudeconvo/issues).