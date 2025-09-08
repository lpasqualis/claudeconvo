"""Command-line interface for claudeconvo.

Provides the main entry point and command-line argument parsing for the
claudeconvo utility, handling session display, theme selection, and file operations.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from .config import determine_theme, load_config
from .constants import (
    CLAUDE_PROJECTS_DIR,
    LIST_ITEM_NUMBER_WIDTH,
    MAX_FILE_INDEX_DIGITS,
    THEME_NAME_DISPLAY_WIDTH,
)
from .diagnostics import run_diagnostics
from .options import ShowOptions
from .session import (
    display_session,
    find_project_root,
    format_file_size,
    get_project_session_dir,
    list_session_files,
    path_to_session_dir,
)
from .themes import THEME_DESCRIPTIONS, THEMES, Colors, get_color_theme
from .utils import (
    get_filename_display_width,
    get_separator_width,
)

# CLI Configuration Constants
DEFAULT_SESSION_COUNT = 1

################################################################################

def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="View Claude Code session history as a conversation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # View last session as conversation
  %(prog)s -l           # List all session files
  %(prog)s -n 2         # Show last 2 sessions
  %(prog)s -t           # Include timestamps
  %(prog)s --no-color   # Disable colored output
  %(prog)s -p /path     # View sessions for specific project path
  %(prog)s --list-projects  # List all projects with sessions

Show options (-s):
  q - Show user messages (default: on)
  w - Show assistant/Claude messages (default: on)
  o - Show tool executions (default: on)
  s - Show session summaries
  h - Show hook executions
  m - Show metadata (uuid, sessionId, version, etc.)
  c - Show command-related messages
  y - Show all system messages
  t - Show full tool details without truncation
  e - Show all error details and warnings
  r - Show API request IDs
  f - Show parent/child relationships
  u - Show all content without truncation
  d - Show performance metrics and token counts
  p - Show working directory (cwd) for each message
  l - Show message level/priority
  k - Show sidechain/parallel messages
  v - Show user type for each message
  i - Show AI model name/version
  a - Enable ALL options

  Special combinations:
  a = Enable ALL options
  A = Disable ALL (start from nothing, then add with lowercase)
  ? = Show what will be enabled/disabled and exit (append to options)
  Uppercase letters EXCLUDE when used with 'a' or from defaults

Examples:
  %(prog)s              # Default: user, assistant, tools
  %(prog)s -sQ          # Default + summaries, but no user messages
  %(prog)s -sa          # Show everything
  %(prog)s -saH         # Show all EXCEPT hooks
  %(prog)s -sA          # Hide everything
  %(prog)s -sAy         # Show ONLY system messages
  %(prog)s -sAqw        # Show ONLY user and assistant (no tools)
  %(prog)s -saH?        # Check what 'all except hooks' will show
  %(prog)s -sAh         # Show ONLY hook executions
        """,
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=DEFAULT_SESSION_COUNT,
        help="Number of recent sessions to show (default: 1, use 0 for all)",
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List all session files without showing content"
    )
    parser.add_argument(
        "-f", "--file", type=str, help="Show specific session file by name or index"
    )
    parser.add_argument(
        "-t", "--timestamp", action="store_true", help="Include timestamps in conversation"
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch session for new entries (press ESC or Ctrl+C to exit)",
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output (same as --theme mono)"
    )
    parser.add_argument(
        "--theme",
        type=str,
        nargs="?",
        const="list",
        choices=list(THEMES.keys()) + ["list"],
        help="Color theme (use --theme without argument to list available themes)",
    )
    parser.add_argument("-p", "--project", type=str, help="Project path to view sessions for")
    parser.add_argument(
        "--list-projects", action="store_true", help="List all projects with session history"
    )
    parser.add_argument(
        "-s", "--show", type=str, default="", help="Show additional info (use -h for details)"
    )
    parser.add_argument(
        "--diagnose", action="store_true", help="Run diagnostic analysis on log format variations"
    )
    parser.add_argument(
        "--diagnose-file", type=str, help="Run diagnostics on a specific session file"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show verbose output in diagnostic mode"
    )
    parser.add_argument(
        "--no-indent", action="store_true", help="Disable indentation alignment for tool results"
    )
    return parser


################################################################################

def handle_diagnostics_mode(args: argparse.Namespace) -> bool:
    """
    Handle diagnostic mode if requested.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if diagnostics were run, False otherwise
    """
    if args.diagnose or args.diagnose_file:
        # Apply theme first for colored output
        config = load_config()
        theme_name = determine_theme(args, config)
        from .themes import Colors

        Colors.set_theme(get_color_theme(theme_name))

        # Run diagnostics
        run_diagnostics(session_file=args.diagnose_file, verbose=args.verbose)
        return True
    return False


################################################################################

def handle_theme_listing(args: argparse.Namespace) -> bool:
    """
    Handle theme listing if requested.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if themes were listed, False otherwise
    """
    if hasattr(args, "theme") and args.theme == "list":
        from .styles import render_inline
        print("\n" + render_inline("header", "Available color themes:"))
        print(render_inline("separator", ""))
        for name, desc in THEME_DESCRIPTIONS.items():
            print(f"  {name:{THEME_NAME_DISPLAY_WIDTH}} - {desc}")
        print(render_inline("separator", ""))
        print("\n" + render_inline("info", "Usage: claudeconvo --theme <theme_name>"))
        print(render_inline("info", "Set default: export CLAUDECONVO_THEME=<theme_name>"))
        print(render_inline("info", "Config file: ~/.claudeconvorc"))
        return True
    return False


################################################################################

def handle_project_listing(args: argparse.Namespace) -> int | None:
    """
    Handle project listing if requested.

    Args:
        args: Parsed command-line arguments

    Returns:
        0 on success, 1 on failure, None if not handling project listing
    """
    if not args.list_projects:
        return None

    from .styles import render_inline

    projects_dir = Path.home() / CLAUDE_PROJECTS_DIR

    if projects_dir.exists():
        projects = sorted([d for d in projects_dir.iterdir() if d.is_dir()])
        msg = f"Found {len(projects)} project(s) with session history:"
        print("\n" + render_inline("header", msg))
        for project in projects:
            # Convert back to path for display
            name = project.name[1:]  # Remove leading dash
            # Handle double dashes (hidden folders)
            name = name.replace("--", "-.")
            # Replace remaining dashes with slashes
            path = "/" + name.replace("-", "/")

            # Count sessions
            session_count = len(list(project.glob("*.jsonl")))
            print(f"  {render_inline('header', path)} ({session_count} sessions)")
        return 0
    else:
        print(render_inline("error", "No projects found"))
        return 1


################################################################################

def get_session_directory(args: argparse.Namespace) -> tuple[str, Path]:
    """
    Get the session directory based on arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Tuple of (project_path, session_dir)
    """
    if args.project:
        # Use specified project path
        project_path = args.project
        session_dir  = path_to_session_dir(project_path)
    else:
        project_path = find_project_root()
        session_dir  = get_project_session_dir()

    return project_path, session_dir


################################################################################

def handle_no_session_directory(project_path: str) -> None:
    """
    Handle the case when no session directory is found.

    Args:
        project_path: Path of the project that has no session directory
    """
    from .styles import render_inline

    print(render_inline("error", f"No session history found for project: {project_path}"))
    tip = "Tip: Use --list-projects to see all projects with sessions"
    print(render_inline("info", tip))
    note = "Note: Both underscores and slashes in paths become dashes in session folders"
    print(render_inline("info", note))
    # Try with underscores converted to dashes
    if "_" in project_path:
        alt_path = project_path.replace("_", "-")
        cmd = f"{os.path.basename(sys.argv[0])} -p {alt_path}"
        print(render_inline("info", f"Try: {cmd}"))


################################################################################

def list_files_only(session_files: list[Path]) -> None:
    """
    Display list of session files.

    Args:
        session_files: List of session file paths to display
    """
    from .styles import render_inline

    print("\n" + render_inline("header", f"Found {len(session_files)} session file(s):"))
    for i, filepath in enumerate(session_files):
        file_stat = filepath.stat()  # Single stat call to avoid TOCTOU
        mtime = datetime.fromtimestamp(file_stat.st_mtime)
        size = file_stat.st_size
        size_str = format_file_size(size)

        # One line per entry with better colors
        timestamp = mtime.strftime("%Y-%m-%d %H:%M")
        filename_width = get_filename_display_width()
        truncated_name = filepath.name[:filename_width]
        idx_str = f"{i+1:{LIST_ITEM_NUMBER_WIDTH}}"
        print(
            f"  {Colors.BOLD}{idx_str}.{Colors.RESET} {truncated_name:{filename_width}} "
            f"{render_inline('info', timestamp + '  ' + size_str.rjust(8))}"
        )


################################################################################

def get_files_to_show(
    args          : argparse.Namespace,
    session_files : list[Path]
) -> list[Path] | None:
    """
    Determine which files to show based on arguments.

    Args:
        args: Parsed command-line arguments
        session_files: Available session files

    Returns:
        List of files to show or None on error
    """
    from .styles import render_inline

    files_to_show = []

    if args.file:
        # Show specific file
        if args.file.isdigit():
            # Treat as index
            try:
                # Add explicit length check before conversion to prevent extremely large numbers
                if len(args.file) > MAX_FILE_INDEX_DIGITS:
                    error_msg = f"Error: Index value too large: {args.file}"
                    print(render_inline("error", error_msg))
                    return None
                idx = int(args.file) - 1
                if 0 <= idx < len(session_files):
                    files_to_show = [session_files[idx]]
                else:
                    error_msg = f"Error: Index {args.file} out of range (1-{len(session_files)})"
                    print(render_inline("error", error_msg))
                    return None
            except (ValueError, OverflowError):
                error_msg = f"Error: Invalid index value: {args.file}"
                print(render_inline("error", error_msg))
                return None
        else:
            # Treat as filename
            for f in session_files:
                if f.name == args.file or f.stem == args.file:
                    files_to_show = [f]
                    break
            if not files_to_show:
                print(render_inline("error", f"Error: File '{args.file}' not found"))
                return None
    else:
        # Show recent files
        if args.number == 0:
            files_to_show = session_files
        else:
            files_to_show = session_files[: args.number]

    return files_to_show


# Removed display_sessions function - now using unified display_session


################################################################################

def main() -> int:
    parser = create_argument_parser()
    args   = parser.parse_args()

    # Handle special modes
    if handle_diagnostics_mode(args):
        return 0

    if handle_theme_listing(args):
        return 0

    # Load config
    config = load_config()

    # Create show options object (use config default if no CLI arg)
    show_str = args.show if args.show else config.get("default_show_options", "")
    show_options = ShowOptions(show_str)

    # Set formatting options based on CLI arguments
    show_options.indent_results = not args.no_indent

    # Determine theme
    theme_name = determine_theme(args, config)

    # Apply theme
    from .styles import set_style

    Colors.set_theme(get_color_theme(theme_name))
    # Also set the formatting style (for now, use default)
    set_style("default")

    # Handle project listing
    project_list_result = handle_project_listing(args)
    if project_list_result is not None:
        return project_list_result

    # Get project session directory
    project_path, session_dir = get_session_directory(args)

    if not session_dir.exists():
        handle_no_session_directory(project_path)
        return 1

    # Get list of session files
    session_files = list_session_files(session_dir)

    if not session_files:
        from .styles import render_inline
        print(render_inline("error", "No session files found"))
        return 1

    # If listing files only
    if args.list:
        list_files_only(session_files)
        return 0

    # Determine which files to show
    files_to_show = get_files_to_show(args, session_files)
    if files_to_show is None:
        return 1

    # Display sessions using unified approach
    for filepath in files_to_show:
        if len(files_to_show) > 1:
            from .styles import render_inline
            sep_width = get_separator_width()
            print("\n" + render_inline("separator", "="* sep_width))
            print(render_inline("header", f"Session: {filepath.name}"))
            file_stat = filepath.stat()  # Single stat call to avoid TOCTOU
            mtime = datetime.fromtimestamp(file_stat.st_mtime)
            date_str = mtime.strftime("%Y-%m-%d %H:%M:%S")
            print(render_inline("info", f"Date: {date_str}"))
            print(render_inline("separator", "="* sep_width))

        # Use unified display function for both normal and watch mode
        display_session(
            filepath, show_options, watch_mode=args.watch, show_timestamp=args.timestamp
        )

        if not args.watch and len(files_to_show) > 1:
            from .styles import render_inline
            sep_width = get_separator_width()
            print("\n" + render_inline("separator", "─" * sep_width))
            print(render_inline("info", "End of session"))

    if not args.watch and len(files_to_show) == 1:
        from .styles import render_inline
        sep_width = get_separator_width()
        print("\n" + render_inline("separator", "─" * sep_width))
        print(render_inline("info", "End of session"))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        from .styles import render_inline
        print("\n" + render_inline("error", "Interrupted"))
        sys.exit(1)
    except BrokenPipeError:
        # Handle pipe errors gracefully (e.g., when piping to head)
        sys.exit(0)
