"""
View Claude Code session history as a conversation.

This utility loads and displays session files stored in ~/.claude/projects/
for the current working directory, formatted as a readable conversation with
colored output for different speakers and tool executions.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import re


# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Message types
    USER = '\033[36m'        # Cyan for user
    ASSISTANT = '\033[32m'   # Green for assistant
    SYSTEM = '\033[33m'      # Yellow for system
    ERROR = '\033[31m'       # Red for errors
    
    # Tool colors
    TOOL_NAME = '\033[35m'   # Magenta for tool names
    TOOL_PARAM = '\033[95m'  # Light magenta for parameters (better on black)
    TOOL_OUTPUT = '\033[90m' # Gray for tool output
    
    # Other
    TIMESTAMP = '\033[37m'   # Light gray/white for timestamps (better visibility)
    SEPARATOR = '\033[37m'   # White for separators
    METADATA = '\033[94m'    # Light blue for metadata


class ShowOptions:
    """Manages display options for filtering session content."""
    
    # Option definitions: (flag_char, attribute_name, description)
    OPTIONS = [
        ('q', 'user', 'Show user messages'),
        ('w', 'assistant', 'Show assistant (Claude) messages'),
        ('s', 'summaries', 'Show session summaries'),
        ('h', 'hooks', 'Show hook executions'),
        ('m', 'metadata', 'Show metadata (uuid, sessionId, version, etc.)'),
        ('c', 'commands', 'Show command-related messages'),
        ('y', 'system', 'Show all system messages'),
        ('t', 'tool_details', 'Show full tool details without truncation'),
        ('o', 'tools', 'Show tool executions'),
        ('e', 'errors', 'Show all error details and warnings'),
        ('r', 'request_ids', 'Show API request IDs'),
        ('f', 'flow', 'Show parent/child relationships'),
        ('u', 'unfiltered', 'Show all content without truncation'),
        ('d', 'diagnostics', 'Show performance metrics and token counts'),
        ('p', 'paths', 'Show working directory (cwd) for each message'),
        ('l', 'levels', 'Show message level/priority'),
        ('k', 'sidechains', 'Show sidechain/parallel messages'),
        ('v', 'user_types', 'Show user type for each message'),
        ('a', 'all', 'Enable all options'),
    ]
    
    # Default options that are enabled without any flags
    DEFAULT_ENABLED = ['user', 'assistant', 'tools']
    
    def __init__(self, options_string=''):
        """Initialize with a string of option flags (e.g., 'shm')."""
        # Set all options to False by default
        for _, attr, _ in self.OPTIONS:
            setattr(self, attr, False)
        
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
        if '?' in options_string:
            # Parse everything except the ?
            temp_options = options_string.replace('?', '')
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
        print("\nShow Options Status:")
        print("-" * 40)
        
        # Group options for better readability
        enabled = []
        disabled = []
        
        for flag_char, attr, desc in self.OPTIONS:
            if attr == 'all':  # Skip the 'all' meta-option
                continue
            is_enabled = getattr(self, attr, False)
            status_line = f"  {flag_char}: {desc}"
            if is_enabled:
                enabled.append(status_line)
            else:
                disabled.append(status_line)
        
        if enabled:
            print(f"{Colors.ASSISTANT}ENABLED:{Colors.RESET}")
            for line in enabled:
                print(f"{Colors.ASSISTANT}{line}{Colors.RESET}")
        
        if disabled:
            print(f"\n{Colors.DIM}DISABLED:{Colors.RESET}")
            for line in disabled:
                print(f"{Colors.DIM}{line}{Colors.RESET}")
        
        print("-" * 40)
        print()
    
    def parse_options_internal(self, options_string):
        """Internal parsing logic (separated for ? handling)."""
        # Start with defaults
        for attr in self.DEFAULT_ENABLED:
            setattr(self, attr, True)
        
        # Process each character left to right
        for char in options_string:
            if char == 'A':
                # Disable ALL
                for _, attr, _ in self.OPTIONS:
                    setattr(self, attr, False)
            elif char == 'a':
                # Enable ALL (except 'all' itself)
                for _, attr, _ in self.OPTIONS:
                    if attr != 'all':
                        setattr(self, attr, True)
            else:
                # Find the matching option
                for flag_char, attr, _ in self.OPTIONS:
                    if char.lower() == flag_char:
                        # Lowercase enables, uppercase disables
                        setattr(self, attr, not char.isupper())
                        break
    
    def should_truncate(self, text_type='default'):
        """Determine if text should be truncated based on options."""
        if self.unfiltered:
            return False
        if text_type == 'tool' and self.tool_details:
            return False
        return True
    
    def get_max_length(self, text_type='default'):
        """Get maximum text length based on options and text type."""
        if not self.should_truncate(text_type):
            return float('inf')
        
        # Different limits for different text types
        limits = {
            'tool_param': 200,
            'tool_result': 500,
            'default': 500,
            'error': 1000 if self.errors else 500,
        }
        return limits.get(text_type, 500)
    


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
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        sessions.append(data)
                    except json.JSONDecodeError as e:
                        print(f"{Colors.ERROR}Warning: Could not parse line: {e}{Colors.RESET}", file=sys.stderr)
    except Exception as e:
        print(f"{Colors.ERROR}Error reading file {filepath}: {e}{Colors.RESET}", file=sys.stderr)
    
    return sessions


def truncate_text(text, max_length=500, force_truncate=False):
    """Truncate text to max length with ellipsis if needed.
    
    Args:
        text: Text to potentially truncate
        max_length: Maximum length (can be float('inf') for no truncation)
        force_truncate: If True, always truncate regardless of max_length being inf
    """
    if not isinstance(text, str):
        return text
    if max_length == float('inf') and not force_truncate:
        return text
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def extract_message_text(message_content):
    """Extract text from various message content formats."""
    if isinstance(message_content, str):
        return message_content
    elif isinstance(message_content, list):
        text_parts = []
        for item in message_content:
            if isinstance(item, dict):
                if 'text' in item:
                    text_parts.append(item['text'])
                elif 'type' in item and item['type'] == 'text' and 'content' in item:
                    text_parts.append(item['content'])
            elif isinstance(item, str):
                text_parts.append(item)
        return '\n'.join(text_parts) if text_parts else None
    elif isinstance(message_content, dict):
        if 'text' in message_content:
            return message_content['text']
        elif 'content' in message_content:
            return extract_message_text(message_content['content'])
    return None


def format_tool_use(entry, show_options):
    """Format tool use information from an entry."""
    output = []
    
    # Look for tool use in message content
    message = entry.get('message', {})
    if isinstance(message, dict):
        content = message.get('content', [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get('type') == 'tool_use':
                    tool_name = item.get('name', 'Unknown Tool')
                    tool_id = item.get('id', '')
                    tool_input = item.get('input', {})
                    
                    output.append(f"\n{Colors.TOOL_NAME}🔧 Tool: {tool_name}{Colors.RESET}")
                    
                    # Show tool ID if requested
                    if show_options.tool_details and tool_id:
                        output.append(f"   {Colors.METADATA}ID: {tool_id}{Colors.RESET}")
                    
                    # Format parameters
                    if tool_input:
                        max_len = show_options.get_max_length('tool_param')
                        for key, value in tool_input.items():
                            value_str = truncate_text(str(value), max_len)
                            output.append(f"   {Colors.TOOL_PARAM}{key}: {value_str}{Colors.RESET}")
    
    return '\n'.join(output) if output else None


def format_tool_result(entry, show_options):
    """Format tool result from an entry."""
    tool_result = entry.get('toolUseResult')
    if tool_result:
        max_len = show_options.get_max_length('tool_result')
        
        if isinstance(tool_result, str):
            # Clean up the result
            result = tool_result.strip()
            if result.startswith('Error:'):
                error_max = show_options.get_max_length('error')
                result = truncate_text(result, error_max)
                return f"{Colors.ERROR}   ❌ {result}{Colors.RESET}"
            else:
                result = truncate_text(result, max_len)
                return f"{Colors.TOOL_OUTPUT}   ✓ Result: {result}{Colors.RESET}"
        elif isinstance(tool_result, list):
            results = []
            for item in tool_result:
                if isinstance(item, dict) and 'content' in item:
                    content = item['content']
                    if isinstance(content, str):
                        content = truncate_text(content, max_len)
                        results.append(f"{Colors.TOOL_OUTPUT}   ✓ {content}{Colors.RESET}")
            return '\n'.join(results) if results else None
    return None


def format_conversation_entry(entry, show_options, show_timestamp=False):
    """Format a single entry as part of a conversation."""
    output = []
    entry_type = entry.get('type', 'unknown')
    
    # Handle summaries
    if entry_type == 'summary':
        if not show_options.summaries:
            return None
        summary = entry.get('summary', 'N/A')
        output.append(f"\n{Colors.SEPARATOR}📝 Summary: {summary}{Colors.RESET}")
        if show_options.metadata and 'leafUuid' in entry:
            output.append(f"   {Colors.METADATA}Session: {entry['leafUuid']}{Colors.RESET}")
        return '\n'.join(output)
    
    # Skip meta entries unless showing metadata
    if entry.get('isMeta', False) and not show_options.metadata:
        return None
    
    # Format timestamp if requested
    timestamp_str = ""
    if show_timestamp and 'timestamp' in entry:
        try:
            dt = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            timestamp_str = f"{Colors.TIMESTAMP}[{dt.strftime('%H:%M:%S')}] {Colors.RESET}"
        except:
            pass
    
    # Add metadata if requested
    metadata_lines = []
    if show_options.metadata:
        meta_items = []
        if 'uuid' in entry:
            meta_items.append(f"uuid:{entry['uuid'][:8]}")
        if 'sessionId' in entry:
            meta_items.append(f"session:{entry['sessionId'][:8]}")
        if 'version' in entry:
            meta_items.append(f"v{entry['version']}")
        if 'gitBranch' in entry:
            meta_items.append(f"git:{entry['gitBranch']}")
        if meta_items:
            metadata_lines.append(f"{Colors.METADATA}[{' | '.join(meta_items)}]{Colors.RESET}")
    
    # Add request IDs if requested
    if show_options.request_ids and 'requestId' in entry:
        metadata_lines.append(f"{Colors.METADATA}Request: {entry['requestId']}{Colors.RESET}")
    
    # Add flow information if requested
    if show_options.flow and 'parentUuid' in entry and entry['parentUuid']:
        metadata_lines.append(f"{Colors.METADATA}Parent: {entry['parentUuid'][:8]}...{Colors.RESET}")
    
    # Add working directory if requested
    if show_options.paths and 'cwd' in entry:
        metadata_lines.append(f"{Colors.METADATA}Path: {entry['cwd']}{Colors.RESET}")
    
    # Add user type if requested
    if show_options.user_types and 'userType' in entry:
        metadata_lines.append(f"{Colors.METADATA}UserType: {entry['userType']}{Colors.RESET}")
    
    # Add level if requested
    if show_options.levels and 'level' in entry:
        metadata_lines.append(f"{Colors.METADATA}Level: {entry['level']}{Colors.RESET}")
    
    # Check for sidechain messages
    if 'isSidechain' in entry and entry['isSidechain']:
        if not show_options.sidechains:
            return None  # Skip sidechain messages unless explicitly requested
        metadata_lines.append(f"{Colors.METADATA}[SIDECHAIN]{Colors.RESET}")
    
    if entry_type == 'user':
        user_shown = False
        
        # Process user message if enabled
        if show_options.user:
            message = entry.get('message', {})
            if isinstance(message, dict):
                content = message.get('content', '')
                text = extract_message_text(content)
                
                # Handle command messages
                is_command = text and (text.startswith('<command-') or text.startswith('<local-command-'))
                if is_command and not show_options.commands:
                    # Skip command messages unless requested
                    pass
                elif text:
                    # Clean up the text if not showing commands
                    if not show_options.commands:
                        text = re.sub(r'<[^>]+>', '', text).strip()  # Remove XML-like tags
                    
                    if text:
                        if metadata_lines:
                            output.extend(metadata_lines)
                        output.append(f"\n{timestamp_str}{Colors.USER}{Colors.BOLD}User:{Colors.RESET} {Colors.USER}{text}{Colors.RESET}")
                        user_shown = True
        
        # Check for tool results (independent of user text)
        if show_options.tools:
            tool_result = format_tool_result(entry, show_options)
            if tool_result:
                # Add metadata if not already added
                if not user_shown and metadata_lines:
                    output.extend(metadata_lines)
                output.append(tool_result)
        
        # Return None only if nothing was shown
        if not output:
            return None
    
    elif entry_type == 'assistant':
        # Process assistant message if enabled
        message = entry.get('message', {})
        assistant_shown = False
        
        if show_options.assistant and isinstance(message, dict):
            content = message.get('content', '')
            text = extract_message_text(content)
            
            if text:
                if metadata_lines:
                    output.extend(metadata_lines)
                max_len = show_options.get_max_length('default')
                text = truncate_text(text, max_len)
                output.append(f"\n{timestamp_str}{Colors.ASSISTANT}{Colors.BOLD}Claude:{Colors.RESET} {Colors.ASSISTANT}{text}{Colors.RESET}")
                assistant_shown = True
        
        # Check for tool uses (independent of assistant text)
        if show_options.tools:
            tool_use = format_tool_use(entry, show_options)
            if tool_use:
                # Add metadata if not already added
                if not assistant_shown and metadata_lines:
                    output.extend(metadata_lines)
                output.append(tool_use)
        
        # Return None only if nothing was shown
        if not output:
            return None
    
    elif entry_type == 'system':
        content = entry.get('content', '')
        
        # Check if this is a hook message
        is_hook = 'hook' in content.lower() or 'PreToolUse' in content or 'PostToolUse' in content
        
        # Determine if we should show this system message
        should_show = False
        
        # System option shows ALL system messages (including hooks)
        if show_options.system:
            should_show = True
        # Hook option can be used to show ONLY hook messages
        elif is_hook and show_options.hooks:
            should_show = True
        # Show important system messages by default (errors, etc.)
        elif content and not content.startswith('[1m') and not is_hook:
            if 'Error' in content or ('completed successfully' not in content):
                should_show = True
        
        if should_show and content:
            if metadata_lines:
                output.extend(metadata_lines)
            # Clean ANSI codes if present
            content = re.sub(r'\[[\d;]*m', '', content)
            output.append(f"\n{timestamp_str}{Colors.SYSTEM}System: {content}{Colors.RESET}")
    
    return '\n'.join(output) if output else None


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
                        help='Disable colored output')
    parser.add_argument('-p', '--project', type=str,
                        help='Project path to view sessions for')
    parser.add_argument('--list-projects', action='store_true',
                        help='List all projects with session history')
    parser.add_argument('-s', '--show', type=str, default='',
                        help='Show additional info (use -h for details)')
    
    args = parser.parse_args()
    
    # Create show options object
    show_options = ShowOptions(args.show)
    
    # Disable colors if requested
    if args.no_color:
        for attr in dir(Colors):
            if not attr.startswith('_'):
                setattr(Colors, attr, '')
    
    # List all projects if requested
    if args.list_projects:
        projects_dir = Path.home() / '.claude' / 'projects'
        if projects_dir.exists():
            projects = sorted([d for d in projects_dir.iterdir() if d.is_dir()])
            print(f"\n{Colors.BOLD}Found {len(projects)} project(s) with session history:{Colors.RESET}")
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
        print(f"{Colors.TIMESTAMP}Tip: Use --list-projects to see all projects with sessions{Colors.RESET}")
        print(f"{Colors.TIMESTAMP}Note: Both underscores and slashes in paths become dashes in session folders{Colors.RESET}")
        # Try with underscores converted to dashes
        if '_' in cwd:
            alt_cwd = cwd.replace('_', '-')
            print(f"{Colors.TIMESTAMP}Try: {os.path.basename(sys.argv[0])} -p {alt_cwd}{Colors.RESET}")
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
            print(f"  {Colors.BOLD}{i+1:3}.{Colors.RESET} {filepath.name[:44]:44} {Colors.TIMESTAMP}{mtime.strftime('%Y-%m-%d %H:%M')}  {size_str:>8}{Colors.RESET}")
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
                print(f"{Colors.ERROR}Error: Index {args.file} out of range (1-{len(session_files)}){Colors.RESET}")
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
            formatted = format_conversation_entry(entry, show_options, show_timestamp=args.timestamp)
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