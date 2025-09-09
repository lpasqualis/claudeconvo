"""Interactive configuration setup for claudeconvo."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Only import termios/tty on Unix-like systems
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

from .constants import CONFIG_FILE_PATH
from .formatters import format_conversation_entry
from .options import ShowOptions
from .styles import STYLE_DESCRIPTIONS
from .themes import THEME_DESCRIPTIONS, Colors, get_color_theme


class MockData:
    """Provides mock conversation data for interactive setup."""

    @staticmethod
    def get_mock_messages() -> List[Dict[str, Any]]:
        """Generate mock messages demonstrating all message types."""
        return [
            {
                "type": "user",
                "content": "Can you help me analyze this Python code for performance issues?",
                "timestamp": "2024-01-15T10:30:00Z",
                "sessionId": "session-123",
                "uuid": "msg-001",
                "cwd": "/Users/demo/project",
                "level": "info",
                "userType": "human"
            },
            {
                "type": "assistant",
                "content": ("I'll analyze your Python code for performance issues. "
                           "Let me examine the file structure first."),
                "timestamp": "2024-01-15T10:30:05Z",
                "model": "claude-3-opus",
                "requestId": "req_abc123"
            },
            {
                "type": "tool",
                "toolName": "Read",
                "params": {"file_path": "/Users/demo/project/main.py", "limit": 100},
                "result": ("def process_data(items):\n"
                          "    result = []\n"
                          "    for item in items:\n"
                          "        # Inefficient nested loop\n"
                          "        for other in items:\n"
                          "            if item != other:\n"
                          "                result.append((item, other))\n"
                          "    return result"),
                "id": "toolu_01Abc123",
                "timestamp": "2024-01-15T10:30:10Z"
            },
            {
                "type": "assistant",
                "content": ("I found a performance issue: The nested loop creates O(n²) "
                           "complexity. Here's an optimized version:"),
                "timestamp": "2024-01-15T10:30:15Z"
            },
            {
                "type": "tool",
                "toolName": "Edit",
                "params": {
                    "file_path": "/Users/demo/project/main.py",
                    "old_string": "for other in items:",
                    "new_string": "for j, other in enumerate(items[i+1:], i+1):"
                },
                "result": "File updated successfully",
                "id": "toolu_02Def456",
                "timestamp": "2024-01-15T10:30:20Z"
            },
            {
                "type": "system",
                "content": "Session saved automatically",
                "timestamp": "2024-01-15T10:30:25Z"
            },
            {
                "type": "summary",
                "content": ("Previous conversation: User asked for help with Python "
                           "performance optimization. Assistant identified O(n²) complexity "
                           "issue and provided optimized solution."),
                "timestamp": "2024-01-15T10:30:30Z"
            },
            {
                "type": "hook",
                "hookType": "pre-commit",
                "content": "Running pre-commit hooks: black, ruff, mypy",
                "timestamp": "2024-01-15T10:30:35Z"
            },
            {
                "type": "error",
                "content": "Warning: Large file detected (>10MB). Consider pagination.",
                "timestamp": "2024-01-15T10:30:40Z"
            },
            {
                "type": "command",
                "content": "/test-runner --verbose",
                "timestamp": "2024-01-15T10:30:45Z"
            }
        ]


class TerminalController:
    """Handles terminal control and input."""

    def __init__(self) -> None:
        """Initialize terminal controller."""
        self.original_settings: Optional[List[Any]] = None

    def setup(self) -> None:
        """Set up terminal for raw input mode."""
        if HAS_TERMIOS and sys.stdin.isatty():
            self.original_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())

    def restore(self) -> None:
        """Restore original terminal settings."""
        if HAS_TERMIOS and self.original_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

    def move_cursor(self, row: int, col: int) -> None:
        """Move cursor to specified position."""
        sys.stdout.write(f'\033[{row};{col}H')
        sys.stdout.flush()

    def get_terminal_size(self) -> Tuple[int, int]:
        """Get terminal dimensions (rows, cols)."""
        try:
            import shutil
            cols, rows = shutil.get_terminal_size((80, 24))
            return rows, cols
        except Exception:
            return 24, 80

    def read_key(self) -> str:
        """Read a single key press."""
        char = sys.stdin.read(1)
        if char == '\x1b':  # Escape sequence
            next_chars = sys.stdin.read(2)
            if next_chars == '[A':
                return 'UP'
            elif next_chars == '[B':
                return 'DOWN'
            elif next_chars == '[C':
                return 'RIGHT'
            elif next_chars == '[D':
                return 'LEFT'
        return char


class SetupState:
    """Manages the state of the interactive setup."""

    def __init__(self) -> None:
        """Initialize setup state."""
        self.show_options = ShowOptions("")  # Start with defaults
        self.theme_index = 0
        self.style_index = 0
        self.themes = ["dark", "light", "solarized-dark", "solarized-light",
                      "dracula", "nord", "mono", "high-contrast"]
        self.styles = ["default", "boxed", "minimal", "compact"]
        self.show_help = False
        self.messages = MockData.get_mock_messages()

    def toggle_option(self, flag: str) -> None:
        """Toggle a show option flag."""
        for flag_char, attr, _ in ShowOptions.OPTIONS:
            if flag_char == flag.lower():
                current = getattr(self.show_options, attr, False)
                setattr(self.show_options, attr, not current)
                break

    def next_theme(self) -> None:
        """Cycle to next theme."""
        self.theme_index = (self.theme_index + 1) % len(self.themes)

    def prev_theme(self) -> None:
        """Cycle to previous theme."""
        self.theme_index = (self.theme_index - 1) % len(self.themes)

    def next_style(self) -> None:
        """Cycle to next style."""
        self.style_index = (self.style_index + 1) % len(self.styles)

    def prev_style(self) -> None:
        """Cycle to previous style."""
        self.style_index = (self.style_index - 1) % len(self.styles)

    @property
    def current_theme(self) -> str:
        """Get current theme name."""
        return self.themes[self.theme_index]

    @property
    def current_style(self) -> str:
        """Get current style name."""
        return self.styles[self.style_index]

    def get_options_string(self) -> str:
        """Get current options as flag string."""
        flags = []
        for flag_char, attr, _ in ShowOptions.OPTIONS:
            if attr != "all" and getattr(self.show_options, attr, False):
                flags.append(flag_char)
        return ''.join(flags) if flags else "(none)"

    def save_config(self) -> str:
        """Save current configuration to file."""
        config_path = Path(CONFIG_FILE_PATH)
        config = {
            "theme": self.current_theme,
            "style": self.current_style,
            "show_options": (
                self.get_options_string() if self.get_options_string() != "(none)" else ""
            ),
            "watch": False  # Default for setup
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # Set secure permissions (user read/write only)
        import stat
        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        return str(config_path)


class InteractiveSetup:
    """Main interactive setup interface."""

    def __init__(self) -> None:
        """Initialize interactive setup."""
        self.controller = TerminalController()
        self.state = SetupState()
        self.running = True

    def render_header(self) -> List[str]:
        """Render the header with current settings."""
        lines = []
        lines.append("╔" + "═" * 78 + "╗")
        lines.append("║ CLAUDECONVO INTERACTIVE SETUP" + " " * 47 + "║")
        lines.append("╟" + "─" * 78 + "╢")

        theme_desc = THEME_DESCRIPTIONS.get(self.state.current_theme, "")[:20]
        style_desc = STYLE_DESCRIPTIONS.get(self.state.current_style, "")[:20]

        lines.append(f"║ Theme: {self.state.current_theme:<12} ({theme_desc:<20}) "
                    f"   [←/→] to change     ║")
        lines.append(f"║ Style: {self.state.current_style:<12} ({style_desc:<20}) "
                    f"   [SPACE] to change   ║")
        lines.append(f"║ Options: {self.state.get_options_string():<60}     ║")
        lines.append("╟" + "─" * 78 + "╢")
        return lines

    def render_messages(self, max_lines: int) -> List[str]:
        """Render mock messages with current settings."""
        lines: List[str] = []
        Colors.set_theme(get_color_theme(self.state.current_theme))
        # Style is set globally via set_style in render()
        from .styles import set_style
        set_style(self.state.current_style)

        for msg in self.state.messages:
            formatted = format_conversation_entry(msg, self.state.show_options, False)
            if formatted:
                # Split into lines and add
                for line in formatted.split('\n'):
                    if len(lines) >= max_lines:
                        break
                    lines.append(line)

        return lines[:max_lines]

    def render_footer(self) -> List[str]:
        """Render the footer with keyboard shortcuts."""
        lines = []
        lines.append("╟" + "─" * 78 + "╢")
        lines.append("║ TOGGLE OPTIONS:" + " " * 61 + "║")

        # Show options in groups
        options = [
            ("q=User", "w=Assistant", "o=Tools", "s=Summary"),
            ("h=Hooks", "m=Metadata", "y=System", "c=Commands"),
            ("t=Tool details", "e=Errors", "r=Request IDs", "f=Flow"),
            ("u=Unfiltered", "d=Diagnostics", "p=Paths", "l=Levels"),
            ("k=Sidechains", "v=User types", "i=Model", "a=All")
        ]

        for group in options:
            line = "║ " + "  ".join(f"{opt:<15}" for opt in group)
            line = line[:78] + " ║"
            lines.append(line)

        lines.append("╟" + "─" * 78 + "╢")
        lines.append("║ [←/→] Change theme  [SPACE] Change style  [?] Help" + " " * 24 + "║")
        lines.append("║ [S] Save & exit     [Q] Quit without saving" + " " * 31 + "║")
        lines.append("╚" + "═" * 78 + "╝")
        return lines

    def render_help(self) -> List[str]:
        """Render help overlay."""
        lines = []
        lines.append("╔" + "═" * 60 + "╗")
        lines.append("║" + " HELP ".center(60) + "║")
        lines.append("╟" + "─" * 60 + "╢")
        lines.append("║ Press letter keys to toggle display options               ║")
        lines.append("║ Use arrow keys to change theme                            ║")
        lines.append("║ Press SPACE to cycle through styles                       ║")
        lines.append("║ Press 'a' to enable all options                          ║")
        lines.append("║ Press 'A' to disable all options                         ║")
        lines.append("║ Press 'S' (uppercase) to save and exit                   ║")
        lines.append("║ Press 'Q' (uppercase) to quit without saving             ║")
        lines.append("║ Press '?' again to close this help                       ║")
        lines.append("╚" + "═" * 60 + "╝")
        return lines

    def render(self) -> None:
        """Render the entire interface."""
        self.controller.clear_screen()
        rows, cols = self.controller.get_terminal_size()

        # Render sections
        header = self.render_header()
        footer = self.render_footer()

        # Calculate space for messages
        header_size = len(header)
        footer_size = len(footer)
        message_space = rows - header_size - footer_size - 1

        messages = self.render_messages(message_space)

        # Output everything
        output = []
        output.extend(header)
        output.extend(messages)

        # Pad if needed
        while len(output) < rows - footer_size - 1:
            output.append("")

        output.extend(footer)

        # Draw
        for line in output:
            print(line[:cols])

        # Draw help overlay if active
        if self.state.show_help:
            help_lines = self.render_help()
            start_row = (rows - len(help_lines)) // 2
            start_col = (cols - 62) // 2

            for i, line in enumerate(help_lines):
                self.controller.move_cursor(start_row + i, start_col)
                sys.stdout.write(line)

        sys.stdout.flush()

    def handle_input(self, key: str) -> None:
        """Handle keyboard input."""
        if key == 'Q':  # Quit without saving
            self.running = False
        elif key == 'S':  # Save and exit
            config_path = self.state.save_config()
            self.controller.restore()
            self.controller.clear_screen()
            print(f"Configuration saved to {config_path}")
            print(f"Theme: {self.state.current_theme}")
            print(f"Style: {self.state.current_style}")
            print(f"Options: -s{self.state.get_options_string()}")
            self.running = False
        elif key == '?':  # Toggle help
            self.state.show_help = not self.state.show_help
        elif key == ' ':  # Space - cycle style
            self.state.next_style()
        elif key == 'LEFT':
            self.state.prev_theme()
        elif key == 'RIGHT':
            self.state.next_theme()
        elif key == 'A':  # Uppercase A - disable all
            for _, attr, _ in ShowOptions.OPTIONS:
                if attr != "all":
                    setattr(self.state.show_options, attr, False)
        elif key == 'a':  # Lowercase a - enable all
            for _, attr, _ in ShowOptions.OPTIONS:
                if attr != "all":
                    setattr(self.state.show_options, attr, True)
        elif key.lower() in 'qwshmcytoefrfudplkvi':  # Toggle options
            self.state.toggle_option(key.lower())

    def run(self) -> None:
        """Run the interactive setup."""
        try:
            self.controller.setup()

            while self.running:
                self.render()
                key = self.controller.read_key()

                if key == '\x03':  # Ctrl+C
                    self.running = False
                else:
                    self.handle_input(key)

        except KeyboardInterrupt:
            pass
        finally:
            self.controller.restore()
            self.controller.clear_screen()


def run_interactive_setup() -> None:
    """Entry point for interactive setup."""
    if not HAS_TERMIOS:
        print("Interactive setup requires a Unix-like terminal (Linux/macOS).")
        print("Please manually create ~/.claudeconvorc with your preferred settings.")
        print("\nExample configuration:")
        print(json.dumps({
            "theme": "dark",
            "style": "default",
            "show_options": "qwo",
            "watch": False
        }, indent=2))
        return

    setup = InteractiveSetup()
    setup.run()
