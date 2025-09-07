"""Command-line interface for claudelog."""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from .config import determine_theme, load_config
from .diagnostics import run_diagnostics
from .formatters import format_conversation_entry
from .options import ShowOptions
from .session import (
    format_file_size,
    get_project_session_dir,
    list_session_files,
    parse_session_file,
    path_to_session_dir,
)
from .themes import THEME_DESCRIPTIONS, THEMES, Colors, get_color_theme


def main():
    parser = argparse.ArgumentParser(
        description='View Claude Code session history as a conversation',
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
        """
    )
    parser.add_argument('-n', '--number', type=int, default=1,
                        help='Number of recent sessions to show (default: 1, use 0 for all)')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List all session files without showing content')
    parser.add_argument('-f', '--file', type=str,
                        help='Show specific session file by name or index')
    parser.add_argument('-t', '--timestamp', action='store_true',
                        help='Include timestamps in conversation')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output (same as --theme mono)')
    parser.add_argument('--theme', type=str, nargs='?', const='list',
                        choices=list(THEMES.keys()) + ['list'],
                        help='Color theme (use --theme without argument to list available themes)')
    parser.add_argument('-p', '--project', type=str,
                        help='Project path to view sessions for')
    parser.add_argument('--list-projects', action='store_true',
                        help='List all projects with session history')
    parser.add_argument('-s', '--show', type=str, default='',
                        help='Show additional info (use -h for details)')
    parser.add_argument('--diagnose', action='store_true',
                        help='Run diagnostic analysis on log format variations')
    parser.add_argument('--diagnose-file', type=str,
                        help='Run diagnostics on a specific session file')
    parser.add_argument('--verbose', action='store_true',
                        help='Show verbose output in diagnostic mode')

    args = parser.parse_args()

    # Handle diagnostics mode
    if args.diagnose or args.diagnose_file:
        # Apply theme first for colored output
        config = load_config()
        theme_name = determine_theme(args, config)
        from .themes import Colors
        Colors.set_theme(get_color_theme(theme_name))
        
        # Run diagnostics
        run_diagnostics(session_file=args.diagnose_file, verbose=args.verbose)
        return 0
    
    # Handle theme listing
    if hasattr(args, 'theme') and args.theme == 'list':
        print("\nAvailable color themes:")
        print("-" * 40)
        for name, desc in THEME_DESCRIPTIONS.items():
            print(f"  {name:16} - {desc}")
        print("-" * 40)
        print("\nUsage: claudelog --theme <theme_name>")
        print("Set default: export CLAUDELOG_THEME=<theme_name>")
        print("Config file: ~/.claudelogrc")
        return 0

    # Load config
    config = load_config()

    # Create show options object (use config default if no CLI arg)
    show_str = args.show if args.show else config.get('default_show_options', '')
    show_options = ShowOptions(show_str)

    # Determine theme
    theme_name = determine_theme(args, config)

    # Apply theme
    from .themes import Colors
    Colors.set_theme(get_color_theme(theme_name))

    # List all projects if requested
    if args.list_projects:
        projects_dir = Path.home() / '.claude' / 'projects'
        if projects_dir.exists():
            projects = sorted([d for d in projects_dir.iterdir() if d.is_dir()])
            msg = f"Found {len(projects)} project(s) with session history:"
            print(f"\n{Colors.BOLD}{msg}{Colors.RESET}")
            for project in projects:
                # Convert back to path for display
                name = project.name[1:]  # Remove leading dash
                # Handle double dashes (hidden folders)
                name = name.replace('--', '-.')
                # Replace remaining dashes with slashes
                path = '/' + name.replace('-', '/')

                # Count sessions
                session_count = len(list(project.glob('*.jsonl')))
                print(f"  {Colors.BOLD}{path}{Colors.RESET} ({session_count} sessions)")
            return 0
        else:
            print(f"{Colors.ERROR}No projects found{Colors.RESET}")
            return 1

    # Get project session directory
    if args.project:
        # Use specified project path
        cwd = args.project
        session_dir = path_to_session_dir(cwd)
    else:
        session_dir = get_project_session_dir()
        cwd = os.getcwd()

    if not session_dir.exists():
        print(f"{Colors.ERROR}No session history found for project: {cwd}{Colors.RESET}")
        tip = "Tip: Use --list-projects to see all projects with sessions"
        print(f"{Colors.TIMESTAMP}{tip}{Colors.RESET}")
        note = "Note: Both underscores and slashes in paths become dashes in session folders"
        print(f"{Colors.TIMESTAMP}{note}{Colors.RESET}")
        # Try with underscores converted to dashes
        if '_' in cwd:
            alt_cwd = cwd.replace('_', '-')
            cmd = f"{os.path.basename(sys.argv[0])} -p {alt_cwd}"
            print(f"{Colors.TIMESTAMP}Try: {cmd}{Colors.RESET}")
        return 1

    # Get list of session files
    session_files = list_session_files(session_dir)

    if not session_files:
        print(f"{Colors.ERROR}No session files found{Colors.RESET}")
        return 1

    # If listing files only
    if args.list:
        print(f"\n{Colors.BOLD}Found {len(session_files)} session file(s):{Colors.RESET}")
        for i, filepath in enumerate(session_files):
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            size = filepath.stat().st_size
            size_str = format_file_size(size)

            # One line per entry with better colors
            timestamp = mtime.strftime('%Y-%m-%d %H:%M')
            print(f"  {Colors.BOLD}{i+1:3}.{Colors.RESET} {filepath.name[:44]:44} "
                  f"{Colors.TIMESTAMP}{timestamp}  {size_str:>8}{Colors.RESET}")
        return 0

    # Determine which files to show
    files_to_show = []

    if args.file:
        # Show specific file
        if args.file.isdigit():
            # Treat as index
            idx = int(args.file) - 1
            if 0 <= idx < len(session_files):
                files_to_show = [session_files[idx]]
            else:
                error_msg = f"Error: Index {args.file} out of range (1-{len(session_files)})"
                print(f"{Colors.ERROR}{error_msg}{Colors.RESET}")
                return 1
        else:
            # Treat as filename
            for f in session_files:
                if f.name == args.file or f.stem == args.file:
                    files_to_show = [f]
                    break
            if not files_to_show:
                print(f"{Colors.ERROR}Error: File '{args.file}' not found{Colors.RESET}")
                return 1
    else:
        # Show recent files
        if args.number == 0:
            files_to_show = session_files
        else:
            files_to_show = session_files[:args.number]

    # Display the sessions as conversations
    for filepath in files_to_show:
        if len(files_to_show) > 1:
            print(f"\n{Colors.SEPARATOR}{'='*70}{Colors.RESET}")
            print(f"{Colors.BOLD}Session: {filepath.name}{Colors.RESET}")
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            print(f"{Colors.TIMESTAMP}Date: {mtime.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
            print(f"{Colors.SEPARATOR}{'='*70}{Colors.RESET}")

        sessions = parse_session_file(filepath)

        if not sessions:
            print(f"{Colors.ERROR}No data found in {filepath.name}{Colors.RESET}")
            continue

        # Display as conversation
        for entry in sessions:
            formatted = format_conversation_entry(
                entry, show_options, show_timestamp=args.timestamp)
            if formatted:
                print(formatted)

        print(f"\n{Colors.SEPARATOR}{'─'*70}{Colors.RESET}")
        print(f"{Colors.TIMESTAMP}End of session{Colors.RESET}")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.ERROR}Interrupted{Colors.RESET}")
        sys.exit(1)
    except BrokenPipeError:
        # Handle pipe errors gracefully (e.g., when piping to head)
        sys.exit(0)
