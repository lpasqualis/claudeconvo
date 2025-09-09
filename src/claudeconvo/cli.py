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
    # Load config to get current defaults
    from .config import load_config
    config = load_config()
    
    # Parse current show options
    from .options import ShowOptions
    current_show = config.get("default_show_options", "qwo")
    show_opts = ShowOptions(current_show)
    
    # Build the show options help with current state
    option_lines = []
    option_lines.append("Show options (-s) [Current config: {}]:".format(current_show))
    
    options_info = [
        ("q", "user", "Show user messages"),
        ("w", "assistant", "Show assistant/Claude messages"),
        ("o", "tools", "Show tool executions"),
        ("s", "summaries", "Show session summaries"),
        ("h", "hooks", "Show hook executions"),
        ("m", "metadata", "Show metadata (uuid, sessionId, version, etc.)"),
        ("c", "commands", "Show command-related messages"),
        ("y", "system", "Show all system messages"),
        ("t", "tool_details", "Show full tool details without truncation"),
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
        ("a", "all", "Enable ALL options"),
    ]
    
    for letter, attr, desc in options_info:
        if letter == 'a':
            option_lines.append(f"  {letter} - {desc}")
        else:
            is_enabled = getattr(show_opts, attr, False)
            status = "ON" if is_enabled else "OFF"
            option_lines.append(f"  {letter} - {desc} (currently: {status})")
    
    show_options_help = "\n".join(option_lines)
    
    parser = argparse.ArgumentParser(
        description="View Claude Code session history as a conversation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s              # View last session as conversation
  %(prog)s -l           # List all session files
  %(prog)s -n 2         # Show last 2 sessions
  %(prog)s -t           # Include timestamps
  %(prog)s --no-color   # Disable colored output
  %(prog)s -p /path     # View sessions for specific project path
  %(prog)s --list-projects  # List all projects with sessions

{show_options_help}

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
  %(prog)s '-saH?'      # Check what 'all except hooks' will show (quote to protect ?)
  %(prog)s -sAh         # Show ONLY hook executions
  %(prog)s -saMFLKVTR   # Director's cut
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
    parser.add_argument(
        "--style",
        type=str,
        nargs="?",
        const="list",
        choices=["default", "boxed", "minimal", "compact", "list"],
        help="Formatting style (use --style without argument to list available styles)",
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
        "--set-default", action="store_true", 
        help="Save current theme, style, and show options as defaults in ~/.claudeconvorc"
    )
    parser.add_argument(
        "--reset-defaults", action="store_true",
        help="Reset all settings to original defaults (removes ~/.claudeconvorc)"
    )
    parser.add_argument(
        "--show-config", action="store_true",
        help="Show complete current configuration (including defaults)"
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Launch interactive configuration setup"
    )
    parser.add_argument(
        "--ai", nargs="+", metavar="CMD",
        help="Automated input for --setup (for testing). Example: --setup --ai 2 s2 t v S"
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

def save_defaults(args: argparse.Namespace, config: dict) -> bool:
    """
    Save current settings as defaults in config file.
    
    Args:
        args: Parsed command-line arguments
        config: Current configuration
        
    Returns:
        True if defaults were saved, False otherwise
    """
    if not args.set_default:
        return False
        
    import json
    from pathlib import Path
    from .styles import render_inline
    
    # Determine what settings to save
    new_config = config.copy()
    
    # Save theme if specified
    if hasattr(args, 'theme') and args.theme and args.theme != 'list':
        new_config['default_theme'] = args.theme
    elif hasattr(args, 'no_color') and args.no_color:
        new_config['default_theme'] = 'mono'
    
    # Save style if specified  
    if hasattr(args, 'style') and args.style and args.style != 'list':
        new_config['default_style'] = args.style
    
    # Save show options if specified
    if hasattr(args, 'show') and args.show:
        new_config['default_show_options'] = args.show
    
    # Save watch mode if specified
    if hasattr(args, 'watch') and args.watch:
        new_config['default_watch'] = True
    
    # Write to config file
    config_path = Path.home() / ".claudeconvorc"
    try:
        with open(config_path, 'w') as f:
            json.dump(new_config, f, indent=2)
        
        print(render_inline("header", "Defaults saved to ~/.claudeconvorc:"))
        if 'default_theme' in new_config:
            print(f"  Theme: {new_config['default_theme']}")
        if 'default_style' in new_config:
            print(f"  Style: {new_config['default_style']}")
        if 'default_show_options' in new_config:
            print(f"  Show options: {new_config['default_show_options']}")
        if 'default_watch' in new_config:
            print(f"  Watch mode: {new_config['default_watch']}")
        return True
    except Exception as e:
        print(render_inline("error", f"Failed to save defaults: {e}"))
        return False


################################################################################

def reset_defaults() -> bool:
    """
    Reset all settings to original defaults by removing config file.
    
    Returns:
        True if defaults were reset, False otherwise
    """
    from pathlib import Path
    from .styles import render_inline
    
    config_path = Path.home() / ".claudeconvorc"
    
    if config_path.exists():
        try:
            config_path.unlink()
            print(render_inline("header", "Defaults reset to original:"))
            print("  Theme: dark")
            print("  Style: default")
            print("  Show options: qwo (user, assistant, tools)")
            print("  Watch mode: off")
            print(render_inline("info", "Config file ~/.claudeconvorc removed"))
            return True
        except Exception as e:
            print(render_inline("error", f"Failed to reset defaults: {e}"))
            return False
    else:
        print(render_inline("info", "No config file found. Already using original defaults."))
        print("  Theme: dark")
        print("  Style: default")
        print("  Show options: qwo (user, assistant, tools)")
        print("  Watch mode: off")
        return True


################################################################################

def show_configuration(args: argparse.Namespace, config: dict) -> bool:
    """
    Display the complete current configuration.
    
    Args:
        args: Parsed command-line arguments
        config: Configuration from file
        
    Returns:
        True if config was displayed, False otherwise
    """
    if not hasattr(args, 'show_config') or not args.show_config:
        return False
        
    from .styles import render_inline
    import json
    import os
    from pathlib import Path
    
    print(render_inline("header", "Current Configuration"))
    print(render_inline("separator", ""))
    
    # Determine effective values (what will actually be used)
    effective_theme = args.theme if hasattr(args, 'theme') and args.theme and args.theme != 'list' else None
    if not effective_theme and hasattr(args, 'no_color') and args.no_color:
        effective_theme = 'mono'
    if not effective_theme:
        effective_theme = os.environ.get('CLAUDECONVO_THEME') or config.get('default_theme', 'dark')
    
    effective_style = args.style if hasattr(args, 'style') and args.style and args.style != 'list' else None
    if not effective_style:
        effective_style = config.get('default_style', 'default')
    
    effective_show = args.show if hasattr(args, 'show') and args.show else config.get('default_show_options', 'qwo')
    
    # For watch, we need to check if it was explicitly set on command line
    # If not explicitly set, use config default
    if hasattr(args, 'watch') and args.watch:
        effective_watch = True
    else:
        effective_watch = config.get('default_watch', False)
    
    # Parse show options to display individual flags
    from .options import ShowOptions
    show_opts = ShowOptions(effective_show)
    flags = []
    flag_map = {
        'user': 'q', 'assistant': 'w', 'tools': 'o', 'summaries': 's',
        'hooks': 'h', 'metadata': 'm', 'commands': 'c', 'system': 'y',
        'tool_details': 't', 'errors': 'e', 'request_ids': 'r', 
        'flow': 'f', 'unfiltered': 'u', 'diagnostics': 'd',
        'paths': 'p', 'levels': 'l', 'sidechains': 'k', 'user_types': 'v',
        'model': 'i'
    }
    for attr, letter in flag_map.items():
        if getattr(show_opts, attr, False):
            flags.append(letter)
        else:
            flags.append(letter.upper())
    flags_str = ''.join(flags)
    
    # Display effective configuration
    print(render_inline("header", "Effective Settings (what will be used):"))
    print(f"  Theme: {effective_theme}")
    print(f"  Style: {effective_style}")
    print(f"  Show options: {effective_show} ({flags_str})")
    print(f"  Watch mode: {effective_watch}")
    print()
    
    # Display config file settings
    config_path = Path.home() / ".claudeconvorc"
    if config_path.exists():
        print(render_inline("header", "Config File (~/.claudeconvorc):"))
        print(f"  Theme: {config.get('default_theme', '(not set)')}")
        print(f"  Style: {config.get('default_style', '(not set)')}")
        
        config_show = config.get('default_show_options', '(not set)')
        if config_show != '(not set)':
            config_show_opts = ShowOptions(config_show)
            config_flags = []
            for attr, letter in flag_map.items():
                if getattr(config_show_opts, attr, False):
                    config_flags.append(letter)
                else:
                    config_flags.append(letter.upper())
            config_flags_str = ''.join(config_flags)
            print(f"  Show options: {config_show} ({config_flags_str})")
        else:
            print(f"  Show options: {config_show}")
            
        print(f"  Watch mode: {config.get('default_watch', '(not set)')}")
        print()
        print(render_inline("info", "Raw config file:"))
        print(json.dumps(config, indent=2))
    else:
        print(render_inline("info", "No config file found (~/.claudeconvorc)"))
    print()
    
    # Display environment variables
    print(render_inline("header", "Environment Variables:"))
    env_theme = os.environ.get('CLAUDECONVO_THEME')
    print(f"  CLAUDECONVO_THEME: {env_theme if env_theme else '(not set)'}")
    print()
    
    # Display command-line overrides
    if any([
        hasattr(args, 'theme') and args.theme and args.theme != 'list',
        hasattr(args, 'style') and args.style and args.style != 'list',
        hasattr(args, 'show') and args.show,
        hasattr(args, 'watch') and args.watch
    ]):
        print(render_inline("header", "Command-line Overrides:"))
        if hasattr(args, 'theme') and args.theme and args.theme != 'list':
            print(f"  --theme {args.theme}")
        if hasattr(args, 'style') and args.style and args.style != 'list':
            print(f"  --style {args.style}")
        if hasattr(args, 'show') and args.show:
            print(f"  --show {args.show}")
        if hasattr(args, 'watch') and args.watch:
            print(f"  --watch")
        print()
    
    # Display built-in defaults
    print(render_inline("header", "Built-in Defaults (use --reset-defaults to restore):"))
    print("  Theme: dark")
    print("  Style: default")
    print("  Show options: qwo (user, assistant, tools)")
    print("  Watch mode: False")
    
    print(render_inline("separator", ""))
    print(render_inline("info", "Priority: CLI args > Environment > Config file > Built-in defaults"))
    
    return True


################################################################################

def handle_style_listing(args: argparse.Namespace) -> bool:
    """
    Handle style listing if requested.

    Args:
        args: Parsed command-line arguments

    Returns:
        True if styles were listed, False otherwise
    """
    if hasattr(args, "style") and args.style == "list":
        from .styles import render_inline, STYLE_DESCRIPTIONS
        print("\n" + render_inline("header", "Available formatting styles:"))
        print(render_inline("separator", ""))
        for name, desc in STYLE_DESCRIPTIONS.items():
            print(f"  {name:12} - {desc}")
        print(render_inline("separator", ""))
        print("\n" + render_inline("info", "Usage: claudeconvo --style <style_name>"))
        print(render_inline("info", "Config file: ~/.claudeconvorc (add default_style setting)"))
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

    if handle_style_listing(args):
        return 0

    # Handle --reset-defaults first (before loading config)
    if hasattr(args, 'reset_defaults') and args.reset_defaults:
        if reset_defaults():
            return 0
    
    # Load config
    config = load_config()
    
    # Handle --show-config if specified
    if show_configuration(args, config):
        return 0
    
    # Handle --setup for interactive configuration
    if args.setup:
        from .simple_setup import run_simple_setup
        automated_commands = getattr(args, 'ai', None)
        run_simple_setup(automated_commands)
        return 0
    
    # Handle --set-default if specified
    if hasattr(args, 'set_default') and args.set_default:
        if save_defaults(args, config):
            return 0

    # Create show options object (use config default if no CLI arg)
    show_str = args.show if args.show else config.get("default_show_options", "")
    show_options = ShowOptions(show_str)

    
    # Apply watch mode default if not specified on CLI
    if not hasattr(args, 'watch'):
        args.watch = False
    if not args.watch and config.get("default_watch", False):
        args.watch = True

    # Determine theme
    theme_name = determine_theme(args, config)

    # Apply theme
    from .styles import set_style

    Colors.set_theme(get_color_theme(theme_name))
    # Set the formatting style (CLI arg > config > default)
    if hasattr(args, 'style') and args.style:
        style_name = args.style
    else:
        style_name = config.get("default_style", "default")
    set_style(style_name)

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
