"""Session file management for claudelog."""

import json
import os
import sys
from pathlib import Path

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
    parts = path.split('/')
    converted_parts = []
    for part in parts:
        if part:  # Skip empty parts from leading/trailing slashes
            # Replace underscores with dashes
            part = part.replace('_', '-')
            if part.startswith('.'):
                # Remove the dot and add extra dash for hidden folders
                converted_parts.append('-' + part[1:])
            else:
                converted_parts.append(part)

    project_name = '-' + '-'.join(converted_parts)
    return Path.home() / '.claude' / 'projects' / project_name


def get_project_session_dir():
    """Get the session directory for the current project."""
    return path_to_session_dir(os.getcwd())


def list_session_files(session_dir):
    """List all session files in the directory, sorted by modification time."""
    if not session_dir.exists():
        return []

    jsonl_files = list(session_dir.glob('*.jsonl'))
    # Sort by modification time (newest first)
    jsonl_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return jsonl_files


def parse_session_file(filepath):
    """Parse a JSONL session file and return its contents."""
    sessions = []
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        sessions.append(data)
                    except json.JSONDecodeError as e:
                        print(f"{Colors.ERROR}Warning: Could not parse line: {e}{Colors.RESET}",
                              file=sys.stderr)
    except Exception as e:
        print(f"{Colors.ERROR}Error reading file {filepath}: {e}{Colors.RESET}", file=sys.stderr)

    return sessions


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"
