"""Simple interactive configuration setup for claudeconvo (no raw terminal required)."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from .constants import CONFIG_FILE_PATH
from .formatters import format_conversation_entry
from .options import ShowOptions
from .styles import STYLE_DESCRIPTIONS, set_style
from .themes import THEME_DESCRIPTIONS, Colors, get_color_theme


def get_demo_messages() -> List[Dict[str, Any]]:
    """Get simple demo messages for setup."""
    return [
        {
            "type": "user",
            "message": {"content": "Hello, can you help me with a Python question?"},
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "type": "assistant",
            "message": {"content": "Of course! I'd be happy to help you with your Python question. What would you like to know?"},
            "timestamp": "2024-01-15T10:30:05Z"
        }
    ]


class SimpleSetup:
    """Simple interactive setup that works everywhere."""
    
    def __init__(self, automated_commands=None):
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
        
        # For show options, if we have a saved value, use 'A' prefix to clear defaults first
        saved_options = config.get("default_show_options", "")
        if saved_options:
            # Use 'A' to clear defaults, then add the saved options
            self.show_options = ShowOptions("A" + saved_options)
        else:
            # No saved options, use defaults
            self.show_options = ShowOptions("")
        
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
        """Display current configuration."""
        print("\n" + "="*60)
        print("CURRENT CONFIGURATION")
        print("="*60)
        print(f"Theme: {self.current_theme} - {THEME_DESCRIPTIONS.get(self.current_theme, '')}")
        print(f"Style: {self.current_style} - {STYLE_DESCRIPTIONS.get(self.current_style, '')}")
        
        # Show enabled options
        enabled = []
        for flag_char, attr, desc in ShowOptions.OPTIONS:
            if attr != "all" and getattr(self.show_options, attr, False):
                enabled.append(f"{flag_char}={desc}")
                
        if enabled:
            print("\nEnabled options:")
            for opt in enabled:
                print(f"  {opt}")
        else:
            print("\nNo options enabled (minimal output)")
            
    def display_menu(self) -> None:
        """Display the menu options."""
        print("\n" + "="*60)
        print("CONFIGURATION MENU")
        print("="*60)
        print("\nTHEMES:")
        for i, theme in enumerate(self.themes, 1):
            marker = " *" if theme == self.current_theme else ""
            print(f"  {i}. {theme}{marker}")
            
        print("\nSTYLES:")
        for i, style in enumerate(self.styles, 1):
            marker = " *" if style == self.current_style else ""
            print(f"  s{i}. {style}{marker}")
            
        print("\nOPTIONS (toggle on/off):")
        options = [
            ("q", "user", "User messages"),
            ("w", "assistant", "Assistant messages"),
            ("o", "tools", "Tool executions"),
            ("t", "tool_details", "Tool details"),
            ("s", "summaries", "Summaries"),
            ("m", "metadata", "Metadata"),
            ("e", "errors", "Error details"),
            ("a", "all", "Enable ALL options"),
        ]
        
        for flag, attr, desc in options:
            status = "ON" if getattr(self.show_options, attr, False) else "OFF"
            print(f"  {flag}. {desc} [{status}]")
            
        print("\nCOMMANDS:")
        print("  v      View sample with current settings")
        print("  /save  Save configuration and exit")
        print("  /exit  Exit without saving")
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
            # For manual input, only lowercase option letters, not slash commands
            result = input(prompt).strip()
            # Only lowercase if it's a single character option (not slash commands)
            if len(result) == 1 and not result.startswith('/'):
                return result.lower()
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
            
            if choice == '/exit':
                print("\nExiting without saving.")
                break
            elif choice == '/save':
                config_path = self.save_config()
                print(f"\nConfiguration saved to {config_path}")
                print("\nYou can now use claudeconvo with your saved settings!")
                break
            elif choice == 'v':
                self.clear_screen()
                self.display_sample()
                if not self.automated_commands:
                    input("\nPress Enter to continue...")
                self.clear_screen()
            elif choice in '12345678':
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
            elif choice in 'qwothsmecyrefduplkvia':
                # Toggle option
                self.toggle_option(choice)
                self.clear_screen()
            else:
                print("\nInvalid choice. Please try again.")
                if not self.automated_commands:
                    input("Press Enter to continue...")
                self.clear_screen()


def run_simple_setup(automated_commands=None) -> None:
    """Entry point for simple setup.
    
    Args:
        automated_commands: Optional list of commands to execute automatically
    """
    setup = SimpleSetup(automated_commands)
    setup.run()