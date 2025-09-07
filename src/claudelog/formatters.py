"""Message formatting functions for claudelog."""

import re
from datetime import datetime

from .themes import Colors
from .parsers.adaptive import AdaptiveParser


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


def extract_message_text(message_content):
    """Extract text from various message content formats.
    
    Uses the adaptive parser for robust content extraction.
    """
    # Create a parser instance (cached internally)
    parser = AdaptiveParser()
    
    # Use parser's extraction method
    return parser._extract_text_from_content(message_content)


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
        except Exception:
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
        parent_id = entry['parentUuid'][:8]
        metadata_lines.append(f"{Colors.METADATA}Parent: {parent_id}...{Colors.RESET}")

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
                is_command = text and (text.startswith('<command-') or
                                      text.startswith('<local-command-'))
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
                        user_label = f"{Colors.USER}{Colors.BOLD}User:{Colors.RESET}"
                        user_prefix = f"\n{timestamp_str}{user_label}"
                        output.append(f"{user_prefix} {Colors.USER}{text}{Colors.RESET}")
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
                assistant_label = f"{Colors.ASSISTANT}{Colors.BOLD}Claude:{Colors.RESET}"
                assistant_prefix = f"\n{timestamp_str}{assistant_label}"
                output.append(f"{assistant_prefix} {Colors.ASSISTANT}{text}{Colors.RESET}")
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
