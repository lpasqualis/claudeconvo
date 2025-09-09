"""Simple interactive configuration setup for claudeconvo (no raw terminal required)."""

import json
import os
from pathlib import Path
from typing import Any

from .constants import CONFIG_FILE_PATH
from .formatters import format_conversation_entry
from .options import ShowOptions
from .styles import set_style
from .themes import Colors, get_color_theme


def get_demo_messages() -> list[dict[str, Any]]:
    """Get comprehensive demo messages from sample JSONL file."""
    # Use the sample conversation file included in the package
    sample_file = Path(__file__).parent / "sample_conversation.jsonl"

    if sample_file.exists():
        # Load messages from the JSONL file
        messages = []
        try:
            with open(sample_file, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))
            return messages
        except (OSError, json.JSONDecodeError):
            # Fall through to use fallback messages
            pass

    # Fallback to simple messages if sample file not found or can't be read
    return [
        {
            "type": "user",
            "message": {"content": "Hello, can you help me with a Python question?"},
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "type": "assistant",
            "message": {"content": ("Of course! I'd be happy to help you with your Python "
                                   "question. What would you like to know?")},
            "timestamp": "2024-01-15T10:30:05Z"
        }
    ]


class SimpleSetup:
    """Simple interactive setup that works everywhere."""

    def __init__(self, automated_commands: list[str] | None = None) -> None:
        """Initialize simple setup.

        Args:
            automated_commands: Optional list of commands to execute automatically
        """
        from .config import load_config

        self.themes = ["dark", "light", "solarized-dark", "solarized-light",
                      "dracula", "nord", "mono", "high-contrast"]
        self.styles = ["default", "boxed", "minimal", "compact"]

        # Load current configuration
        config = load_config()
        self.current_theme = config.get("default_theme", "dark")
        self.current_style = config.get("default_style", "default")

        # Initialize show options from saved config or defaults
        saved_options = config.get("default_show_options", "")
        self.show_options = ShowOptions(saved_options)

        self.sample_messages = get_demo_messages()
        self.automated_commands = automated_commands or []
        self.command_index = 0

    def clear_screen(self) -> None:
        """Clear screen in a cross-platform way."""
        # Use ANSI escape codes for safer cross-platform screen clearing
        # \033[2J clears the screen, \033[H moves cursor to home position
        print('\033[2J\033[H', end='', flush=True)

    def display_sample(self) -> None:
        """Display sample output with current settings."""
        print("\n" + "="*60)
        print("SAMPLE OUTPUT WITH CURRENT SETTINGS")
        print("="*60 + "\n")

        Colors.set_theme(get_color_theme(self.current_theme))
        set_style(self.current_style)

        for msg in self.sample_messages:
            output = format_conversation_entry(msg, self.show_options)
            if output:
                print(output)

    def display_current_settings(self) -> None:
        """Display current configuration as command line."""
        # Build the equivalent command line
        cmd_parts = ["claudeconvo"]

        # Add show options if any are enabled
        flags = []
        for flag_char, attr, _ in ShowOptions.OPTIONS:
            if attr != "all" and getattr(self.show_options, attr, False):
                flags.append(flag_char)

        if flags:
            cmd_parts.append(f"-s{''.join(flags)}")

        # Add theme if not default
        if self.current_theme != "dark":
            cmd_parts.append(f"--theme {self.current_theme}")

        # Add style if not default
        if self.current_style != "default":
            cmd_parts.append(f"--style {self.current_style}")

        # Display as a command line
        print("\n" + "="*60)
        print("CURRENT SETTINGS")
        print("="*60)
        print(" ".join(cmd_parts))

    def display_menu(self) -> None:
        """Display the menu options."""
        print("\n" + "="*60)
        print("CONFIGURATION MENU")
        print("="*60)

        # Display themes and styles side by side
        print("\nTHEMES:                          STYLES:")
        for i in range(max(len(self.themes), len(self.styles))):
            # Theme column
            if i < len(self.themes):
                theme = self.themes[i]
                marker = " *" if theme == self.current_theme else ""
                theme_str = f"  {i+1}. {theme}{marker}"
            else:
                theme_str = ""

            # Style column
            if i < len(self.styles):
                style = self.styles[i]
                marker = " *" if style == self.current_style else ""
                style_str = f"s{i+1}. {style}{marker}"
            else:
                style_str = ""

            # Print both columns aligned
            print(f"{theme_str:<32} {style_str}")

        print("\nOPTIONS (toggle on/off):")

        # Define all options
        all_options = [
            ("q", "user", "User messages"),
            ("w", "assistant", "Assistant messages"),
            ("o", "tools", "Tool executions"),
            ("t", "tool_details", "Tool details"),
            ("s", "summaries", "Summaries"),
            ("h", "hooks", "Hook calls"),
            ("m", "metadata", "Metadata"),
            ("c", "commands", "Slash commands"),
            ("y", "system", "System messages"),
            ("e", "errors", "Error details"),
            ("r", "request_ids", "Request IDs"),
            ("f", "flow", "Parent/child relationships"),
            ("u", "unfiltered", "Untruncated content"),
            ("d", "diagnostics", "Performance metrics"),
            ("p", "paths", "Working directories"),
            ("l", "levels", "Message levels"),
            ("k", "sidechains", "Sidechain messages"),
            ("v", "user_types", "User types"),
            ("i", "model", "AI model names"),
        ]

        # Split into enabled and disabled (excluding 'all' option)
        enabled_options = []
        disabled_options = []

        for flag, attr, desc in all_options:
            is_enabled = getattr(self.show_options, attr, False)
            if is_enabled:
                enabled_options.append((flag, desc))
            else:
                disabled_options.append((flag, desc))

        # Display in two columns: enabled on left, disabled on right
        print("  ENABLED:                       DISABLED:")
        max_rows = max(len(enabled_options), len(disabled_options))

        for i in range(max_rows):
            # Enabled column
            if i < len(enabled_options):
                flag, desc = enabled_options[i]
                left_str = f"  {flag}. {desc}"
            else:
                left_str = ""

            # Disabled column
            if i < len(disabled_options):
                flag, desc = disabled_options[i]
                right_str = f"{flag}. {desc}"
            else:
                right_str = ""

            print(f"{left_str:<32} {right_str}")

        # Special option for 'all'
        all_enabled = all(
            getattr(self.show_options, attr, False)
            for _, attr, _ in all_options
        )
        print(f"\n  a. Enable ALL options [{('ON' if all_enabled else 'OFF')}]")

        print("\nCOMMANDS:")
        print("  V or [ENTER]  View sample with current settings")
        print("  X             Exit without saving (quick exit)")
        print("  /set          Set as defaults (equivalent to --set-defaults)")
        print("  /reset        Reset to defaults")
        print("  /exit         Exit without saving")
        print("\n" + "="*60)

    def toggle_option(self, flag: str) -> None:
        """Toggle a show option."""
        if flag == 'a':
            # Toggle all
            current_all = all(
                getattr(self.show_options, attr, False)
                for _, attr, _ in ShowOptions.OPTIONS
                if attr != "all"
            )
            for _, attr, _ in ShowOptions.OPTIONS:
                if attr != "all":
                    setattr(self.show_options, attr, not current_all)
        else:
            for flag_char, attr, _ in ShowOptions.OPTIONS:
                if flag_char == flag:
                    current = getattr(self.show_options, attr, False)
                    setattr(self.show_options, attr, not current)
                    break

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        # Reset theme and style
        self.current_theme = "dark"
        self.current_style = "default"

        # Reset show options to defaults
        self.show_options = ShowOptions('')  # This will use DEFAULT_ENABLED

    def save_config(self) -> str:
        """Save configuration to file."""
        from .config import load_config

        config_path = Path(CONFIG_FILE_PATH)

        # Load existing config to preserve other settings
        existing_config = load_config()

        # Build options string
        flags = []
        for flag_char, attr, _ in ShowOptions.OPTIONS:
            if attr != "all" and getattr(self.show_options, attr, False):
                flags.append(flag_char)

        # Update config with new values (using correct keys)
        config = {
            "default_theme": self.current_theme,
            "default_style": self.current_style,
            "default_show_options": ''.join(flags) if flags else "",
            "default_watch": existing_config.get("default_watch", False)
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # Set secure permissions (user read/write only)
        import stat
        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        return str(config_path)

    def get_next_command(self, prompt: str = "\nEnter your choice: ") -> str:
        """Get next command from automated list or user input.

        Args:
            prompt: Prompt to show for user input

        Returns:
            Next command string
        """
        if self.automated_commands:
            # In automated mode
            if self.command_index < len(self.automated_commands):
                cmd = self.automated_commands[self.command_index]
                self.command_index += 1
                print(f"{prompt}{cmd} [automated]")
                return cmd
            else:
                # No more commands, exit automatically
                print(f"{prompt}/exit [automated - end of commands]")
                return '/exit'
        else:
            # For manual input, return as-is (case sensitive)
            result = input(prompt).strip()
            return result

    def run(self) -> None:
        """Run the simple interactive setup."""
        self.clear_screen()
        print("\nWELCOME TO CLAUDECONVO INTERACTIVE SETUP")
        print("This will help you configure your preferred settings.\n")

        while True:
            self.display_current_settings()
            self.display_menu()

            choice = self.get_next_command("\nEnter your choice: ").strip()

            # Handle empty input - view sample (same as 'V')
            if not choice:
                choice = 'V'

            # Handle exit shortcuts
            # ESC key representations or 'x' for quick exit
            if choice in ('\x1b', 'ESC', 'Esc', 'esc', '^[', 'x', 'X'):
                choice = '/exit'

            if choice == '/exit':
                print("\nExiting without saving.")
                break
            elif choice == '/set':
                config_path = self.save_config()
                print(f"\nDefaults set in {config_path}")
                print("\nYour settings are now the default for claudeconvo!")
                break
            elif choice == '/reset':
                self.reset_to_defaults()
                print("\nReset to default settings.")
                self.clear_screen()
            elif choice == 'V':
                self.clear_screen()
                self.display_sample()
                if not self.automated_commands:
                    input("\nPress Enter to continue...")
                self.clear_screen()
            elif len(choice) == 1 and choice in '12345678':
                # Theme selection
                idx = int(choice) - 1
                if 0 <= idx < len(self.themes):
                    self.current_theme = self.themes[idx]
                    self.clear_screen()
            elif choice.startswith('s') and len(choice) == 2 and choice[1] in '1234':
                # Style selection
                idx = int(choice[1]) - 1
                if 0 <= idx < len(self.styles):
                    self.current_style = self.styles[idx]
                    self.clear_screen()
            elif len(choice) == 1 and choice.lower() in 'qwothsmecyrefduplkvia':
                # Toggle option (accept both upper and lowercase)
                self.toggle_option(choice.lower())
                self.clear_screen()
            else:
                print("\nInvalid choice. Please try again.")
                if not self.automated_commands:
                    input("Press Enter to continue...")
                self.clear_screen()


def run_simple_setup(automated_commands: list[str] | None = None) -> None:
    """Entry point for simple setup.

    Args:
        automated_commands: Optional list of commands to execute automatically
    """
    setup = SimpleSetup(automated_commands)
    setup.run()
