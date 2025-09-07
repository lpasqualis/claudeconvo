"""Utility functions for claudelog."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import (
    FILENAME_DISPLAY_WIDTH,
    UUID_DISPLAY_LENGTH,
)


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
            return int(os.environ.get("COLUMNS", 80))
        except (ValueError, TypeError):
            return 80


def get_separator_width() -> int:
    """Get the width for separator lines based on terminal width.

    Returns:
        Width for separator lines
    """
    term_width = get_terminal_width()
    # Use terminal width but cap at a reasonable maximum
    return min(term_width - 2, 120)  # Leave some margin, cap at 120


def get_filename_display_width() -> int:
    """Get the width for filename display based on terminal width.

    Returns:
        Width for filename display
    """
    term_width = get_terminal_width()
    if term_width < 80:
        # Narrow terminal - use less space for filenames
        return max(20, term_width // 3)
    elif term_width < 120:
        # Normal terminal
        return FILENAME_DISPLAY_WIDTH
    else:
        # Wide terminal - can show more of the filename
        return min(60, term_width // 2)


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
        import sys

        print(f"Warning: Failed to load config from {config_path}: {e}", file=sys.stderr)
        return default
