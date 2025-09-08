"""Display options management for claudelog."""

import sys

from .constants import DEFAULT_TRUNCATION_LIMITS


class ShowOptions:
    """Manages display options for filtering session content."""

    # Option definitions: (flag_char, attribute_name, description)
    OPTIONS = [
        ("q", "user", "Show user messages"),
        ("w", "assistant", "Show assistant (Claude) messages"),
        ("s", "summaries", "Show session summaries"),
        ("h", "hooks", "Show hook executions"),
        ("m", "metadata", "Show metadata (uuid, sessionId, version, etc.)"),
        ("c", "commands", "Show command-related messages"),
        ("y", "system", "Show all system messages"),
        ("t", "tool_details", "Show full tool details without truncation"),
        ("o", "tools", "Show tool executions"),
        ("e", "errors", "Show all error details and warnings"),
        ("r", "request_ids", "Show API request IDs"),
        ("f", "flow", "Show parent/child relationships"),
        ("u", "unfiltered", "Show all content without truncation"),
        ("d", "diagnostics", "Show performance metrics and token counts"),
        ("p", "paths", "Show working directory (cwd) for each message"),
        ("l", "levels", "Show message level/priority"),
        ("k", "sidechains", "Show sidechain/parallel messages"),
        ("v", "user_types", "Show user type for each message"),
        ("i", "model", "Show AI model name/version"),
        ("a", "all", "Enable all options"),
    ]

    # Default options that are enabled without any flags
    DEFAULT_ENABLED = ["user", "assistant", "tools"]

    def __init__(self, options_string=""):
        """Initialize with a string of option flags (e.g., 'shm')."""
        # Set all options to False by default
        for _, attr, _ in self.OPTIONS:
            setattr(self, attr, False)

        # Debug mode for internal error reporting (not user-facing)
        self.debug = False
        
        # Formatting options (not part of the flag system)
        self.indent_results = True  # Default to enabled

        # Enable defaults if no options specified
        if not options_string:
            for attr in self.DEFAULT_ENABLED:
                setattr(self, attr, True)
        else:
            # Parse the options string
            self.parse_options(options_string)

    def parse_options(self, options_string):
        """Parse option string and set corresponding flags.

        Lowercase letters enable options, uppercase letters disable them.
        - 'a' = enable all options
        - 'A' = disable all (start from nothing, useful with lowercase to add specific items)
        - 'Ay' = disable all, then enable only system messages
        - 'aH' = enable all except hooks
        - '?' = print what will be shown/hidden and exit

        Without 'a' or 'A', starts with defaults (user, assistant, tools) then modifies.
        """
        # Check for help request
        if "?" in options_string:
            # Parse everything except the ?
            temp_options = options_string.replace("?", "")
            if temp_options:
                self.parse_options_internal(temp_options)
            else:
                # Set defaults if no other options
                for attr in self.DEFAULT_ENABLED:
                    setattr(self, attr, True)
            self.print_status()
            sys.exit(0)
        else:
            self.parse_options_internal(options_string)

    def print_status(self):
        """Print the current status of all options."""
        # Import styles here to avoid circular import
        from .styles import render_inline

        print("\n" + render_inline("header", "Show Options Status:"))
        print(render_inline("separator", ""))

        # Group options for better readability
        enabled = []
        disabled = []

        for flag_char, attr, desc in self.OPTIONS:
            if attr == "all":  # Skip the 'all' meta-option
                continue
            is_enabled = getattr(self, attr, False)
            status_line = f"  {flag_char}: {desc}"
            if is_enabled:
                enabled.append(status_line)
            else:
                disabled.append(status_line)

        if enabled:
            from .themes import Colors
            print(f"{Colors.ASSISTANT}ENABLED:{Colors.RESET}")
            for line in enabled:
                print(f"{Colors.ASSISTANT}{line}{Colors.RESET}")

        if disabled:
            from .themes import Colors
            print(f"\n{Colors.DIM}DISABLED:{Colors.RESET}")
            for line in disabled:
                print(f"{Colors.DIM}{line}{Colors.RESET}")

        print(render_inline("separator", ""))
        print()

    def parse_options_internal(self, options_string):
        """Internal parsing logic (separated for ? handling)."""
        # Start with defaults
        for attr in self.DEFAULT_ENABLED:
            setattr(self, attr, True)

        # Process each character left to right
        for char in options_string:
            if char == "A":
                # Disable ALL
                for _, attr, _ in self.OPTIONS:
                    setattr(self, attr, False)
            elif char == "a":
                # Enable ALL (except 'all' itself)
                for _, attr, _ in self.OPTIONS:
                    if attr != "all":
                        setattr(self, attr, True)
            else:
                # Find the matching option
                for flag_char, attr, _ in self.OPTIONS:
                    if char.lower() == flag_char:
                        # Lowercase enables, uppercase disables
                        setattr(self, attr, not char.isupper())
                        break

    def should_truncate(self, text_type="default"):
        """Determine if text should be truncated based on options."""
        if self.unfiltered:
            return False
        # Check if tool_details is enabled for any tool-related text type
        if self.tool_details and text_type in ("tool", "tool_param", "tool_result"):
            return False
        return True

    def get_max_length(self, text_type="default"):
        """Get maximum text length based on options and text type."""
        if not self.should_truncate(text_type):
            return float("inf")

        # Use predefined constants for truncation limits
        if text_type == "error":
            if self.errors:
                return DEFAULT_TRUNCATION_LIMITS["error"]
            return DEFAULT_TRUNCATION_LIMITS["error_short"]

        return DEFAULT_TRUNCATION_LIMITS.get(text_type, DEFAULT_TRUNCATION_LIMITS["default"])
