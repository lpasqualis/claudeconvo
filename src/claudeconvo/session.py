"""Session file management for claudeconvo.

Provides functionality for discovering, parsing, and displaying Claude session files,
with support for security validation, format adaptation, and watch mode.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .constants import (
    BYTES_PER_KB,
    BYTES_PER_MB,
    CLAUDE_PROJECTS_DIR,
    ESC_KEY_CODE,
    MAX_FILE_SIZE,
    MAX_FILE_SIZE_MB,
    MAX_LINE_SIZE,
    WATCH_POLL_INTERVAL,
)
from .parsers.adaptive import AdaptiveParser
from .styles import render, render_inline
from .tool_tracker import ToolInvocationTracker
from .utils import log_debug

# Session processing constants
ROOT_MARKERS = [".git", ".claude", ".hg", ".svn", "pyproject.toml", "setup.py", "package.json"]


################################################################################

def path_to_session_dir(path: str) -> Path:
    """
    Convert a file path to Claude's session directory naming convention.

    Args:
        path: File system path to convert

    Returns:
        Path object for the session directory
    """
    # Convert path to Claude's naming convention
    # Format: Leading dash, path with slashes replaced by dashes
    # Hidden folders (starting with .) get the dot removed and double dash
    # Underscores also become dashes
    parts           = path.split("/")
    converted_parts = []

    for part in parts:
        if part:  # Skip empty parts from leading/trailing slashes
            # Replace underscores with dashes
            part = part.replace("_", "-")
            if part.startswith("."):
                # Remove the dot and add extra dash for hidden folders
                converted_parts.append("-" + part[1:])
            else:
                converted_parts.append(part)

    project_name = "-" + "-".join(converted_parts)
    return Path.home() / CLAUDE_PROJECTS_DIR / project_name


################################################################################

def find_project_root(start_path: str | None = None) -> str:
    """
    Find the project root by looking for markers like .git, .claude, etc.

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to project root, or original path if no root found
    """
    if start_path is None:
        start_path = os.getcwd()

    current = Path(start_path).resolve()

    # Walk up the directory tree
    while current != current.parent:
        # Check for any root markers
        for marker in ROOT_MARKERS:
            if (current / marker).exists():
                return str(current)
        current = current.parent

    # If no project root found, return the original path
    return start_path


################################################################################

def get_project_session_dir() -> Path:
    """
    Get the session directory for the current project.

    Returns:
        Path to the session directory for the current project
    """
    # Find the project root first
    project_root = find_project_root()
    return path_to_session_dir(project_root)


################################################################################

def list_session_files(session_dir: Path) -> list[Path]:
    """
    List all session files in the directory, sorted by modification time.

    Args:
        session_dir: Directory to search for session files

    Returns:
        List of session file paths, sorted by modification time (newest first)
    """
    if not session_dir.exists():
        return []

    jsonl_files = list(session_dir.glob("*.jsonl"))
    # Sort by modification time (newest first)
    jsonl_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return jsonl_files


################################################################################

def parse_session_file(filepath: Path) -> list[dict[str, Any]]:
    """
    Parse a JSONL session file and return its contents.

    Args:
        filepath: Path to the JSONL session file to parse

    Returns:
        List of parsed session entries
    """
    sessions: list[dict[str, Any]] = []
    parser   = AdaptiveParser()  # Will auto-load config if available
    tracker  = ToolInvocationTracker()  # Track tool invocations

    # Validate file path
    filepath = Path(filepath)

    # Check if path is a symlink and refuse to follow symlinks for security
    try:
        if filepath.is_symlink():
            err_msg = "Security: Refusing to follow symlink for session file"
            print(render_inline("error", err_msg), file=sys.stderr)
            return sessions
    except (OSError, TypeError) as e:
        # Path doesn't exist or is mocked in tests - continue with validation
        log_debug(f"Could not check symlink status for {filepath}: {e}")

    # Resolve to absolute path after symlink check
    filepath      = filepath.resolve()
    home_sessions = Path.home() / CLAUDE_PROJECTS_DIR

    # Ensure the file is within the expected Claude sessions directory
    if not (home_sessions in filepath.parents or filepath.parent == home_sessions):
        err_msg = "Security: Refusing to read file outside Claude sessions directory"
        print(render_inline("error", err_msg), file=sys.stderr)
        return sessions

    try:
        with open(filepath, encoding='utf-8') as f:
            # Check file size using fstat on open file handle to prevent TOCTOU
            try:
                import os

                file_stat = os.fstat(f.fileno())
                if file_stat.st_size > MAX_FILE_SIZE:
                    size_str = format_file_size(file_stat.st_size)
                    max_mb   = f"{MAX_FILE_SIZE_MB}MB"
                    err_msg  = f"Warning: File too large ({size_str}). "
                    err_msg += f"Maximum size is {max_mb}"
                    print(render_inline("warning", err_msg), file=sys.stderr)
                    return sessions
            except OSError as e:
                # Log for debugging if needed but continue processing
                # File size check is a safety measure, not a hard requirement
                log_debug(f"Could not check file size for {filepath}: {e}")

            for line_num, line in enumerate(f, 1):
                # Check line size before processing to prevent memory exhaustion
                if len(line) > MAX_LINE_SIZE:
                    err_msg = f"Warning: Line {line_num} exceeds size limit ({len(line)} > {MAX_LINE_SIZE}), skipping"
                    print(render_inline("warning", err_msg), file=sys.stderr)
                    continue
                    
                line = line.strip()
                if line:
                    try:
                        raw_data    = json.loads(line)
                        # Use the adaptive parser to normalize the entry
                        parsed_data = parser.parse_entry(raw_data)

                        # Track tool invocations
                        tracker.track_tool_use(parsed_data)

                        # If this is any tool result, enhance it with tool info
                        if tracker.is_tool_result(parsed_data):
                            tool_info = tracker.get_tool_info_for_entry(parsed_data)
                            if tool_info:
                                # Special handling for Task results
                                if tracker.is_task_result(parsed_data):
                                    parsed_data["_task_info"] = tool_info
                                else:
                                    parsed_data["_tool_info"] = tool_info

                        sessions.append(parsed_data)
                    except json.JSONDecodeError as e:
                        err_msg = f"Warning: JSON parse error on line {line_num}: {e}"
                        print(render_inline("warning", err_msg), file=sys.stderr)
                    except (ValueError, TypeError, KeyError, AttributeError) as e:
                        # Parser errors - log but don't expose full error details
                        err_type = type(e).__name__
                        err_msg = f"Warning: Parse error on line {line_num}: {err_type}"
                        print(render_inline("warning", err_msg), file=sys.stderr)
                        # Don't include raw conversation data to prevent PII exposure
                        # Only include minimal error information
                        error_entry = {
                            "_parse_error": err_type,
                            "_line_number": line_num,
                            "type": "parse_error"
                        }
                        sessions.append(error_entry)
    except (OSError, PermissionError) as e:
        # Sanitize error message to avoid exposing sensitive paths
        err_msg = f"Error reading session file: {type(e).__name__}"
        print(render_inline("error", err_msg), file=sys.stderr)
    except UnicodeDecodeError:
        # Handle encoding issues
        err_msg = "Error reading session file: Encoding error"
        print(render_inline("error", err_msg), file=sys.stderr)
    except MemoryError:
        # Handle large file memory issues
        err_msg = "Error reading session file: Out of memory"
        print(render_inline("error", err_msg), file=sys.stderr)

    return sessions


################################################################################

def display_session(
    filepath       : Path,
    show_options   : Any,
    watch_mode     : bool = False,
    show_timestamp : bool = False
) -> None:
    """
    Display a session file with optional watch mode.

    Args:
        filepath: Path to session file
        show_options: ShowOptions instance for filtering/formatting
        watch_mode: If True, watch for new entries continuously
        show_timestamp: Whether to include timestamps in output
    """
    import time

    from .formatters import format_conversation_entry

    if not filepath.exists():
        print(render_inline("error", f"Session file not found: {filepath}"), file=sys.stderr)
        return

    # Set up keyboard handling for ESC detection (needed for finally block)
    old_settings = None

    if watch_mode:
        print(render("system", content=f"Watching session: {filepath.name}"))
        print(render_inline("info", "Press ESC or Ctrl+C to exit") + "\n")
        try:
            import select
            import termios
            import tty

            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except (ImportError, OSError, AttributeError):
            old_settings = None
            print(render_inline("info", "Press Ctrl+C to exit") + "\n")

    try:
        displayed_count = 0

        while True:
            # Parse the current session file
            sessions = parse_session_file(filepath)

            # Display any new entries
            for i, entry in enumerate(sessions[displayed_count:], displayed_count):
                formatted = format_conversation_entry(
                    entry, show_options, show_timestamp=show_timestamp
                )
                if formatted:
                    print(formatted)
                    if watch_mode:
                        sys.stdout.flush()  # Ensure immediate output in watch mode

            displayed_count = len(sessions)

            if not watch_mode:
                break  # Normal mode: exit after displaying all entries

            # Watch mode: check for ESC key and continue monitoring
            if old_settings:
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ord(ch) == ESC_KEY_CODE:  # ESC key
                        print(render("system", content="Stopped watching"))
                        break

            time.sleep(WATCH_POLL_INTERVAL)  # Poll interval

    except KeyboardInterrupt:
        if watch_mode:
            print(render("system", content="Interrupted"))
    finally:
        # Restore terminal settings
        if old_settings:
            try:
                import termios

                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except (ImportError, OSError, AttributeError):
                pass


################################################################################

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes to format

    Returns:
        Human-readable size string (e.g., "1.2KB", "5.3MB")
    """
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes}B"
    elif size_bytes < BYTES_PER_MB:
        return f"{size_bytes/BYTES_PER_KB:.1f}KB"
    else:
        return f"{size_bytes/BYTES_PER_MB:.1f}MB"
