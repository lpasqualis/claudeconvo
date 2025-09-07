"""File watching functionality for claudelog."""

import json
import sys
import time
from pathlib import Path
from typing import Set

# Platform-specific imports for keyboard handling
try:
    import select
    import termios
    import tty

    HAS_TERMIOS = True
except ImportError:
    # Windows or other non-Unix systems
    HAS_TERMIOS = False

from .formatters import format_conversation_entry
from .parsers.adaptive import AdaptiveParser
from .themes import Colors
from .utils import log_debug

# Constants
ESC_KEY_CODE = 27  # ASCII code for ESC key
WATCH_POLL_INTERVAL = 0.5  # Seconds between file checks


def check_for_esc() -> bool:
    """Check if ESC key has been pressed (non-blocking).

    Returns:
        True if ESC was pressed, False otherwise
    """
    if HAS_TERMIOS:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ord(ch) == ESC_KEY_CODE:
                return True
    # On Windows, ESC detection not supported, rely on Ctrl+C only
    return False


def watch_session_file(filepath: Path, show_options, show_timestamp: bool = False) -> None:
    """Watch a session file for new entries and display them as they appear.

    Args:
        filepath: Path to the session file to watch
        show_options: ShowOptions instance for filtering/formatting
        show_timestamp: Whether to include timestamps in output
    """
    # Set terminal to raw mode to capture ESC key (Unix only)
    old_settings = None
    if HAS_TERMIOS:
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except (termios.error, AttributeError):
            # Failed to set terminal mode, continue without ESC support
            old_settings = None

    try:
        print(f"\n{Colors.SYSTEM}Watching session: {filepath.name}{Colors.RESET}")
        if HAS_TERMIOS and old_settings:
            print(f"{Colors.DIM}Press ESC or Ctrl+C to exit{Colors.RESET}\n")
        else:
            print(f"{Colors.DIM}Press Ctrl+C to exit{Colors.RESET}\n")

        # Keep track of entries we've already displayed
        seen_entries: Set[str] = set()
        parser = AdaptiveParser()
        last_size = 0

        while True:
            try:
                # Check for ESC key
                if check_for_esc():
                    print(f"\n{Colors.SYSTEM}Stopped watching{Colors.RESET}")
                    break

                # Check if file has grown
                current_size = filepath.stat().st_size
                if current_size > last_size:
                    # Read and parse the file
                    with open(filepath, encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue

                            # Create a unique key for this entry
                            # Using the raw line as key to detect duplicates
                            entry_key = line

                            if entry_key not in seen_entries:
                                seen_entries.add(entry_key)

                                # Parse the new entry
                                try:
                                    raw_entry = json.loads(line)
                                    entry = parser.parse_entry(raw_entry)

                                    # Format and display
                                    formatted = format_conversation_entry(
                                        entry, show_options, show_timestamp=show_timestamp
                                    )
                                    if formatted:
                                        print(formatted)
                                        sys.stdout.flush()  # Ensure immediate output

                                except json.JSONDecodeError as e:
                                    # Skip malformed JSON entries silently
                                    # This is expected for incomplete or corrupted lines
                                    log_debug(f"Skipping malformed JSON at line {line_num}: {e}")
                                except (ValueError, TypeError, KeyError, AttributeError) as e:
                                    # Log parsing errors for debugging without exposing details
                                    # These might indicate format changes or unexpected data
                                    if show_options.debug:
                                        err_name = type(e).__name__
                                        msg = f"Debug: Failed to parse entry: {err_name}"
                                        print(f"{Colors.DIM}{msg}{Colors.RESET}", file=sys.stderr)

                    last_size = current_size

                # Small delay to avoid excessive CPU usage
                time.sleep(WATCH_POLL_INTERVAL)

            except KeyboardInterrupt:
                print(f"\n{Colors.SYSTEM}Interrupted{Colors.RESET}")
                break

    finally:
        # Restore terminal settings (Unix only)
        if HAS_TERMIOS and old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except (termios.error, AttributeError):
                pass  # Ignore errors when restoring terminal


def watch_sessions(files_to_watch: list, show_options, show_timestamp: bool = False) -> None:
    """Watch one or more session files for new entries.

    Args:
        files_to_watch: List of file paths to watch
        show_options: ShowOptions instance for filtering/formatting
        show_timestamp: Whether to include timestamps in output
    """
    if len(files_to_watch) > 1:
        print(
            f"{Colors.WARNING}Warning: Watching multiple files is not yet supported.{Colors.RESET}"
        )
        print(
            f"{Colors.WARNING}Watching only the first file: {files_to_watch[0].name}{Colors.RESET}"
        )

    # For now, only watch the first file
    watch_session_file(files_to_watch[0], show_options, show_timestamp)
