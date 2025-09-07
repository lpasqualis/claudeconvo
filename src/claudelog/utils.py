"""Utility functions for claudelog."""

import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import (
    FILENAME_DISPLAY_WIDTH,
    MAX_TOOL_WIDTH,
    MIN_TOOL_WIDTH,
    SEPARATOR_WIDTH,
    TOOL_WIDTH_DIVISOR,
    TOOL_WIDTH_HALF_DIVISOR,
    UUID_DISPLAY_LENGTH,
)

# Terminal width constants
DEFAULT_TERMINAL_WIDTH = 80
MAX_CONTENT_WIDTH = 120
MIN_COMFORTABLE_WIDTH = 80
WIDE_TERMINAL_THRESHOLD = 120
TERMINAL_MARGIN = 2


def get_terminal_width() -> int:
    """Get the current terminal width.

    Returns:
        Terminal width in characters, defaults to 80 if not detectable
    """
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        # Fallback to environment variable or default
        try:
            return int(os.environ.get("COLUMNS", DEFAULT_TERMINAL_WIDTH))
        except (ValueError, TypeError):
            return DEFAULT_TERMINAL_WIDTH


def get_separator_width() -> int:
    """Get the width for separator lines based on terminal width.

    Returns:
        Width for separator lines
    """
    term_width = get_terminal_width()
    # Use terminal width but cap at a reasonable maximum
    # Leave some margin, cap at reasonable width
    return min(term_width - TERMINAL_MARGIN, MAX_CONTENT_WIDTH)


def get_filename_display_width() -> int:
    """Get the width for filename display based on terminal width.

    Returns:
        Width for filename display
    """
    term_width = get_terminal_width()
    if term_width < MIN_COMFORTABLE_WIDTH:
        # Narrow terminal - use less space for filenames
        return max(MIN_TOOL_WIDTH, term_width // TOOL_WIDTH_DIVISOR)
    elif term_width < WIDE_TERMINAL_THRESHOLD:
        # Normal terminal
        return FILENAME_DISPLAY_WIDTH
    else:
        # Wide terminal - can show more of the filename
        return min(MAX_TOOL_WIDTH, term_width // TOOL_WIDTH_HALF_DIVISOR)


def format_uuid(uuid: str) -> str:
    """Format a UUID for display with consistent truncation.

    Args:
        uuid: Full UUID string

    Returns:
        Truncated UUID for display
    """
    if not uuid:
        return ""
    return uuid[:UUID_DISPLAY_LENGTH]


def format_with_color(text: str, color: str, reset: str) -> str:
    """Format text with color codes.

    Args:
        text: Text to format
        color: Color code to apply
        reset: Reset code

    Returns:
        Formatted string with color codes
    """
    return f"{color}{text}{reset}"


def format_error(text: str, colors) -> str:
    """Format an error message.

    Args:
        text: Error text
        colors: Colors object with ERROR and RESET attributes

    Returns:
        Formatted error string
    """
    return format_with_color(text, colors.ERROR, colors.RESET)


def format_success(text: str, colors) -> str:
    """Format a success message.

    Args:
        text: Success text
        colors: Colors object with ASSISTANT and RESET attributes

    Returns:
        Formatted success string
    """
    return format_with_color(text, colors.ASSISTANT, colors.RESET)


def format_info(text: str, colors) -> str:
    """Format an info message.

    Args:
        text: Info text
        colors: Colors object with DIM and RESET attributes

    Returns:
        Formatted info string
    """
    return format_with_color(text, colors.DIM, colors.RESET)


def format_bold(text: str, colors) -> str:
    """Format text in bold.

    Args:
        text: Text to make bold
        colors: Colors object with BOLD and RESET attributes

    Returns:
        Formatted bold string
    """
    return format_with_color(text, colors.BOLD, colors.RESET)


def sanitize_terminal_output(text: str, strip_all_escapes: bool = False) -> str:
    """Sanitize text for safe terminal output.

    Removes or escapes potentially dangerous terminal control sequences
    while preserving legitimate ANSI color codes (unless strip_all requested).

    Args:
        text: Text to sanitize
        strip_all_escapes: If True, remove all escape sequences including colors

    Returns:
        Sanitized text safe for terminal output
    """
    if not text:
        return text

    # Remove null bytes and other control characters (except newlines, tabs)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ch >= " ")

    if strip_all_escapes:
        # Remove all ANSI escape sequences
        text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)
        text = re.sub(r"\x1b\].*?\x07", "", text)  # OSC sequences
        text = re.sub(r"\x1b[PX^_].*?\x1b\\", "", text)  # Other escape sequences
    else:
        # Selectively remove dangerous sequences while keeping color codes
        # Remove OSC (Operating System Command) sequences - can set window title, etc
        text = re.sub(r"\x1b\].*?\x07", "", text)
        text = re.sub(r"\x1b\].*?\x1b\\", "", text)

        # Remove APC, DCS, PM, SOS sequences
        text = re.sub(r"\x1b[PX^_].*?\x1b\\", "", text)

        # Remove cursor movement and dangerous CSI sequences
        # but keep SGR (colors) - they end with 'm'
        text = re.sub(r"\x1b\[(?![0-9;]*m)[0-9;]*[A-HJKSTfsu]", "", text)

        # Remove any remaining ESC characters not part of ANSI codes
        text = re.sub(r"(?<!\x1b\[)\x1b(?!\[)", "", text)

    return text


def load_json_config(config_path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load a JSON configuration file with error handling.

    Args:
        config_path: Path to the configuration file
        default: Default configuration to use if file doesn't exist or fails to load

    Returns:
        Configuration dictionary
    """
    if default is None:
        default = {}

    if not config_path or not config_path.exists():
        return default

    try:
        with open(config_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        # Log error for debugging but continue with defaults

        log_debug(f"Failed to load config from {config_path}: {e}")
        return default


def log_debug(message: str) -> None:
    """Log debug messages if debug mode is enabled.

    Args:
        message: Debug message to log
    """
    # Check if debug mode is enabled via environment variable
    if os.environ.get("CLAUDELOG_DEBUG"):
        print(f"[DEBUG] {message}", file=sys.stderr)

    # Also use standard logging in case it's configured
    logging.debug(message)
