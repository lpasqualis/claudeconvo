"""Session file management for claudelog."""

import json
import os
import sys
from pathlib import Path

from .constants import (
    BYTES_PER_KB,
    BYTES_PER_MB,
    CLAUDE_PROJECTS_DIR,
    MAX_FILE_SIZE,
    MAX_FILE_SIZE_MB,
)
from .parsers.adaptive import AdaptiveParser
from .themes import Colors


def path_to_session_dir(path):
    """Convert a file path to Claude's session directory naming convention.

    Args:
        path: File system path to convert

    Returns:
        Path object for the session directory
    """
    # Convert path to Claude's naming convention
    # Format: Leading dash, path with slashes replaced by dashes
    # Hidden folders (starting with .) get the dot removed and double dash
    # Underscores also become dashes
    parts = path.split("/")
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


def find_project_root(start_path=None):
    """Find the project root by looking for markers like .git, .claude, etc.

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to project root, or original path if no root found
    """
    if start_path is None:
        start_path = os.getcwd()

    current = Path(start_path).resolve()

    # Markers that indicate a project root
    root_markers = [".git", ".claude", ".hg", ".svn", "pyproject.toml", "setup.py", "package.json"]

    # Walk up the directory tree
    while current != current.parent:
        # Check for any root markers
        for marker in root_markers:
            if (current / marker).exists():
                return str(current)
        current = current.parent

    # If no project root found, return the original path
    return start_path


def get_project_session_dir():
    """Get the session directory for the current project."""
    # Find the project root first
    project_root = find_project_root()
    return path_to_session_dir(project_root)


def list_session_files(session_dir):
    """List all session files in the directory, sorted by modification time."""
    if not session_dir.exists():
        return []

    jsonl_files = list(session_dir.glob("*.jsonl"))
    # Sort by modification time (newest first)
    jsonl_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return jsonl_files


def parse_session_file(filepath):
    """Parse a JSONL session file and return its contents."""
    sessions = []
    parser = AdaptiveParser()  # Will auto-load config if available

    # Validate file path
    filepath = Path(filepath).resolve()
    home_sessions = Path.home() / CLAUDE_PROJECTS_DIR

    # Ensure the file is within the expected Claude sessions directory
    if not (home_sessions in filepath.parents or filepath.parent == home_sessions):
        err_msg = f"{Colors.ERROR}Security: Refusing to read file outside Claude sessions directory"
        print(f"{err_msg}{Colors.RESET}", file=sys.stderr)
        return sessions

    # Check file size to prevent memory exhaustion
    try:
        file_size = filepath.stat().st_size
        if file_size > MAX_FILE_SIZE:
            size_str = format_file_size(file_size)
            max_mb = f"{MAX_FILE_SIZE_MB}MB"
            err_msg = f"{Colors.ERROR}Warning: File too large ({size_str}). "
            err_msg += f"Maximum size is {max_mb}"
            print(f"{err_msg}{Colors.RESET}", file=sys.stderr)
            return sessions
    except OSError:
        pass  # Continue if we can't get file size

    try:
        with open(filepath) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        raw_data = json.loads(line)
                        # Use the adaptive parser to normalize the entry
                        parsed_data = parser.parse_entry(raw_data)
                        sessions.append(parsed_data)
                    except json.JSONDecodeError as e:
                        err_msg = f"{Colors.ERROR}Warning: JSON parse error on line {line_num}: {e}"
                        print(f"{err_msg}{Colors.RESET}", file=sys.stderr)
                    except (ValueError, TypeError, KeyError, AttributeError) as e:
                        # Parser errors - log but don't expose full error details
                        err_type = type(e).__name__
                        err_msg = f"{Colors.ERROR}Warning: Parse error on line {line_num}: "
                        err_msg += err_type
                        print(f"{err_msg}{Colors.RESET}", file=sys.stderr)
                        # Add raw data with sanitized error flag
                        raw_data["_parse_error"] = type(e).__name__
                        sessions.append(raw_data)
    except Exception as e:
        print(f"{Colors.ERROR}Error reading file {filepath}: {e}{Colors.RESET}", file=sys.stderr)

    return sessions


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes}B"
    elif size_bytes < BYTES_PER_MB:
        return f"{size_bytes/BYTES_PER_KB:.1f}KB"
    else:
        return f"{size_bytes/BYTES_PER_MB:.1f}MB"
