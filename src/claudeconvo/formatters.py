"""Message formatting functions for claudeconvo.

This module provides comprehensive formatting capabilities for Claude session data,
handling message display, tool execution results, and conversation presentation.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from .parsers.adaptive import AdaptiveParser
from .styles import render, render_inline
from .utils import format_uuid, sanitize_terminal_output

# Formatting constants
DEFAULT_MAX_LENGTH = 500

################################################################################

def truncate_text(
    text         : str | Any,
    max_length   : int | float = DEFAULT_MAX_LENGTH,
    force_truncate: bool = False
) -> str | Any:
    """
    Truncate text to max length with ellipsis if needed.

    Args:
        text: Text to potentially truncate
        max_length: Maximum length (can be float('inf') for no truncation)
        force_truncate: If True, always truncate regardless of max_length being inf

    Returns:
        Truncated text or original text/object if no truncation needed
    """
    if not isinstance(text, str):
        return text
    if max_length == float("inf") and not force_truncate:
        return text
    if len(text) > max_length:
        return text[:int(max_length)] + "..."
    return text

################################################################################

def extract_message_text(message_content: Any) -> str:
    """
    Extract text from various message content formats.

    Uses the adaptive parser for robust content extraction.

    Args:
        message_content: Content to extract text from

    Returns:
        Extracted text string
    """
    # Create a parser instance (cached internally)
    parser = AdaptiveParser()

    # Use parser's extraction method
    result = parser._extract_text_from_content(message_content)
    return result or ""

################################################################################

def format_tool_use(
    entry        : dict[str, Any],
    show_options : Any
) -> str | None:
    """
    Format tool use information from an entry.

    Args:
        entry: Session entry containing tool use data
        show_options: Display options configuration

    Returns:
        Formatted tool use string or None if no tool use found
    """
    output = []

    # Look for tool use in message content
    message = entry.get("message", {})
    if isinstance(message, dict):
        content = message.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_name  = item.get("name", "Unknown Tool")
                    tool_id    = item.get("id", "")
                    tool_input = item.get("input", {})

                    # Render tool invocation
                    output.append(render("tool_invocation", name=tool_name))

                    # Show tool ID if requested
                    if show_options.tool_details and tool_id:
                        output.append(render("metadata", content=f"   ID: {tool_id}"))

                    # Format parameters only if tool_details is enabled
                    if tool_input and show_options.tool_details:
                        max_len = show_options.get_max_length("tool_param")
                        for key, value in tool_input.items():
                            value_str = truncate_text(str(value), max_len)
                            output.append(render("tool_parameter", key=key, value=value_str))

    return ''.join(output) if output else None


################################################################################

def format_tool_result(
    entry        : dict[str, Any],
    show_options : Any
) -> str | None:
    """
    Format tool result from an entry.

    Args:
        entry: Session entry containing tool result data
        show_options: Display options configuration

    Returns:
        Formatted tool result string or None if no result found
    """
    tool_result = entry.get("toolUseResult")
    if tool_result:
        max_len = show_options.get_max_length("tool_result")

        if isinstance(tool_result, str):
            # Clean up the result
            result = tool_result.strip()
            if result.startswith("Error:"):
                error_max = show_options.get_max_length("error")
                result    = truncate_text(result, error_max)
                return render("tool_result_error", content=result)
            else:
                result = truncate_text(result, max_len)
                return render("tool_result_success", content=result)
        elif isinstance(tool_result, list):
            results = []
            for item in tool_result:
                if isinstance(item, dict) and "content" in item:
                    content = item["content"]
                    if isinstance(content, str):
                        content = truncate_text(content, max_len)
                        results.append(render("tool_result_success", content=content))
            return "\n".join(results) if results else None
    return None


################################################################################

def _format_summary_entry(
    entry        : dict[str, Any],
    show_options : Any
) -> str | None:
    """
    Format a summary entry.

    Args:
        entry: Session entry containing summary data
        show_options: Display options configuration

    Returns:
        Formatted summary string or None if summaries disabled
    """
    if not show_options.summaries:
        return None

    output  = []
    summary = entry.get("summary", "N/A")
    output.append(render("summary", content=summary))

    if show_options.metadata and "leafUuid" in entry:
        output.append(render("metadata", content=f"   Session: {entry['leafUuid']}"))

    return ''.join(output)


################################################################################

def _format_timestamp(
    entry          : dict[str, Any],
    show_timestamp : bool
) -> str:
    """
    Format timestamp for an entry.

    Args:
        entry: Session entry that may contain timestamp
        show_timestamp: Whether to format timestamp

    Returns:
        Formatted timestamp string or empty string
    """
    timestamp_str = ""
    if show_timestamp and "timestamp" in entry:
        try:
            dt            = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            timestamp_str = render_inline("timestamp", content=dt.strftime('%H:%M:%S'))
        except (ValueError, TypeError, AttributeError):
            # ValueError: Invalid timestamp format
            # TypeError: timestamp is not a string
            # AttributeError: timestamp object missing expected method
            pass  # Keep timestamp_str as empty string on parse failure
    return timestamp_str


################################################################################

def _build_metadata_lines(
    entry        : dict[str, Any],
    show_options : Any
) -> list[str] | None:
    """
    Build metadata lines for an entry.

    Args:
        entry: Session entry containing metadata
        show_options: Display options configuration

    Returns:
        List of formatted metadata lines or None to signal skip
    """
    metadata_lines = []

    # Model information (for assistant messages)
    if show_options.model:
        message = entry.get("message", {})
        if isinstance(message, dict) and message.get("model"):
            model_name = message["model"]
            # Format the model name to be more readable
            if "claude-" in model_name:
                # Extract the meaningful parts: e.g., "claude-opus-4-1-20250805" -> "Opus 4.1"
                parts = model_name.split("-")
                if len(parts) >= 3:
                    tier = parts[1].capitalize()  # opus -> Opus
                    version = parts[2] if len(parts) > 2 else ""
                    if len(parts) > 3 and parts[3]:
                        version += f".{parts[3]}"
                    model_display = f"{tier} {version}"
                else:
                    model_display = model_name
            else:
                model_display = model_name
            metadata_lines.append(render("metadata", content=f"Model: {model_display}"))

    # Basic metadata
    if show_options.metadata:
        meta_items = []
        if "uuid" in entry:
            meta_items.append(f"uuid:{format_uuid(entry['uuid'])}")
        if "sessionId" in entry:
            meta_items.append(f"session:{format_uuid(entry['sessionId'])}")
        if "version" in entry:
            meta_items.append(f"v{entry['version']}")
        if "gitBranch" in entry:
            meta_items.append(f"git:{entry['gitBranch']}")
        if meta_items:
            metadata_lines.append(render("metadata", content=' | '.join(meta_items)))

    # Request IDs
    if show_options.request_ids and "requestId" in entry:
        metadata_lines.append(render("metadata", content=f"Request: {entry['requestId']}"))

    # Flow information
    if show_options.flow and "parentUuid" in entry and entry["parentUuid"]:
        parent_id = format_uuid(entry["parentUuid"])
        metadata_lines.append(render("metadata", content=f"Parent: {parent_id}..."))

    # Working directory
    if show_options.paths and "cwd" in entry:
        metadata_lines.append(render("metadata", content=f"Path: {entry['cwd']}"))

    # User type
    if show_options.user_types and "userType" in entry:
        metadata_lines.append(render("metadata", content=f"UserType: {entry['userType']}"))

    # Level
    if show_options.levels and "level" in entry:
        metadata_lines.append(render("metadata", content=f"Level: {entry['level']}"))

    # Sidechain indicator
    if "isSidechain" in entry and entry["isSidechain"]:
        if not show_options.sidechains:
            return None  # Signal to skip this entry
        metadata_lines.append(render("metadata", content="SIDECHAIN"))

    return metadata_lines


################################################################################

def format_conversation_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    show_timestamp : bool = False
) -> str | None:
    """
    Format a single entry as part of a conversation.

    Args:
        entry: Session entry to format
        show_options: Display options configuration
        show_timestamp: Whether to include timestamps

    Returns:
        Formatted conversation entry or None if entry should be skipped
    """
    output: list[str] = []
    entry_type = entry.get("type", "unknown")

    # Handle summaries
    if entry_type == "summary":
        return _format_summary_entry(entry, show_options)

    # Skip meta entries unless showing metadata
    if entry.get("isMeta", False) and not show_options.metadata:
        return None

    # Format timestamp
    timestamp_str = _format_timestamp(entry, show_timestamp)

    # Build metadata lines
    metadata_lines = _build_metadata_lines(entry, show_options)
    if metadata_lines is None:  # Sidechain skip signal
        return None

    if entry_type == "user":
        return _format_user_entry(entry, show_options, timestamp_str, metadata_lines)

    elif entry_type == "assistant":
        return _format_assistant_entry(entry, show_options, timestamp_str, metadata_lines)

    elif entry_type == "system":
        return _format_system_entry(entry, show_options, timestamp_str, metadata_lines)

    return ''.join(output) if output else None


################################################################################

def _extract_and_format_tool_result(
    message       : dict[str, Any],
    label         : str,
    show_options  : Any,
    timestamp_str : str = ""
) -> list[str] | None:
    """
    Extract and format tool result content from a message.

    Args:
        message: The message dict containing the tool result
        label: The formatted label for the tool result
        show_options: ShowOptions instance
        timestamp_str: Optional timestamp string

    Returns:
        List of output lines or None if no content found
    """
    output = []

    if not isinstance(message, dict):
        return None

    content = message.get("content", [])
    if not (isinstance(content, list) and len(content) > 0):
        return None

    first_item = content[0]
    if not (isinstance(first_item, dict) and first_item.get("type") == "tool_result"):
        return None

    result_content = first_item.get("content", [])
    text           = None

    # Handle both string and list formats
    if isinstance(result_content, str):
        # Direct string content
        text = result_content
    elif isinstance(result_content, list) and result_content:
        # List format - find text item
        for item in result_content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                break

    if not text:
        return None

    max_len = show_options.get_max_length("tool_result")
    text    = truncate_text(text, max_len)

    # Let the style template handle all formatting
    from .themes import Colors
    
    # Render the tool result with label using the style template
    rendered_result = render("tool_result_with_label", 
                           label=label,
                           content=text,
                           timestamp=timestamp_str)
    
    if rendered_result:
        output.append(rendered_result)
    else:
        # Fallback if style doesn't define tool_result_with_label
        output.append(f"   {Colors.TOOL_NAME}✓ {label}{Colors.RESET}")
        rendered_content = render("tool_result_success", content=text)
        if rendered_content:
            output.append(rendered_content)

    return output


################################################################################

def _format_user_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    timestamp_str  : str,
    metadata_lines : list[str] | None
) -> str | None:
    """
    Format a user entry.

    Args:
        entry: User session entry to format
        show_options: Display options configuration
        timestamp_str: Formatted timestamp string
        metadata_lines: Pre-built metadata lines

    Returns:
        Formatted user entry or None if entry should be skipped
    """
    output     = []
    user_shown = False

    # Check if this is a Task/subagent result
    task_info = entry.get("_task_info")
    tool_info = entry.get("_tool_info")

    if task_info and show_options.tools:
        # This is a Task result - format it specially
        if metadata_lines:
            output.extend(metadata_lines)

        # Create appropriate label based on task type
        task_name = task_info.get("name", "Task")
        if task_name == "Task":
            subagent_type = task_info.get("subagent_type", "unknown")
            description = task_info.get("description", "")
            if subagent_type != "unknown":
                label = f"Subagent ({subagent_type}):"
            else:
                label = "Task Result:"

            # Add description if available
            if description and show_options.tool_details:
                output.append(render("metadata", content=description))
        else:
            label = f"{task_name} Result:"

        # Extract and format the actual content
        message = entry.get("message", {})
        result_lines = _extract_and_format_tool_result(message, label, show_options, timestamp_str)
        if result_lines:
            output.extend(result_lines)
            user_shown = True

        # If we formatted it as a task, we're done
        if user_shown:
            return ''.join(output) if output else None

    elif tool_info and show_options.tools:
        # This is a regular tool result - format it as such
        if metadata_lines:
            output.extend(metadata_lines)

        # Create label for regular tool
        tool_name = tool_info.get("name", "Tool")
        label = f"{tool_name} Result:"

        # Extract and format the actual content
        message = entry.get("message", {})
        result_lines = _extract_and_format_tool_result(message, label, show_options, timestamp_str)
        if result_lines:
            output.extend(result_lines)
            user_shown = True

        # If we formatted it as a tool result, we're done
        if user_shown:
            return ''.join(output) if output else None

    # Process user message if enabled (not a Task or tool result)
    if show_options.user and not task_info and not tool_info:
        message = entry.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", "")
            text = extract_message_text(content)

            # Handle command messages
            is_command = text and (
                text.startswith("<command-") or text.startswith("<local-command-")
            )
            if is_command and not show_options.commands:
                # Skip command messages unless requested
                pass
            elif text:
                # Clean up the text if not showing commands
                if not show_options.commands:
                    text = re.sub(r"<[^>]+>", "", text).strip()  # Remove XML-like tags

                if text:
                    if metadata_lines:
                        output.extend(metadata_lines)
                    user_msg = render("user", content=text)
                    # Prepend timestamp if present
                    if timestamp_str:
                        output.append(timestamp_str + user_msg)
                    else:
                        output.append(user_msg)
                    user_shown = True

    # Check for tool results (independent of user text)
    # Skip if this was already handled as a Task or tool result
    if show_options.tools and not task_info and not tool_info:
        tool_result = format_tool_result(entry, show_options)
        if tool_result:
            # Add metadata if not already added
            if not user_shown and metadata_lines:
                output.extend(metadata_lines)
            output.append(tool_result)

    # Return None only if nothing was shown
    return ''.join(output) if output else None


################################################################################

def _format_assistant_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    timestamp_str  : str,
    metadata_lines : list[str] | None
) -> str | None:
    """
    Format an assistant entry.

    Args:
        entry: Assistant session entry to format
        show_options: Display options configuration
        timestamp_str: Formatted timestamp string
        metadata_lines: Pre-built metadata lines

    Returns:
        Formatted assistant entry or None if entry should be skipped
    """
    output          = []
    message         = entry.get("message", {})
    assistant_shown = False

    if show_options.assistant and isinstance(message, dict):
        content = message.get("content", "")
        text = extract_message_text(content)

        if text:
            if metadata_lines:
                output.extend(metadata_lines)
            max_len       = show_options.get_max_length("default")
            text          = truncate_text(text, max_len)
            assistant_msg = render("assistant", content=text)
            # Prepend timestamp if present
            if timestamp_str:
                output.append(timestamp_str + assistant_msg)
            else:
                output.append(assistant_msg)
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
    return ''.join(output) if output else None


################################################################################

def _format_system_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    timestamp_str  : str,
    metadata_lines : list[str] | None
) -> str | None:
    """
    Format a system entry.

    Args:
        entry: System session entry to format
        show_options: Display options configuration
        timestamp_str: Formatted timestamp string
        metadata_lines: Pre-built metadata lines

    Returns:
        Formatted system entry or None if entry should be skipped
    """
    output  = []
    content = entry.get("content", "")

    # Check if this is a hook message
    is_hook = "hook" in content.lower() or "PreToolUse" in content or "PostToolUse" in content

    # Determine if we should show this system message
    should_show = False

    # System option shows ALL system messages (including hooks)
    if show_options.system:
        should_show = True
    # Hook option can be used to show ONLY hook messages
    elif is_hook and show_options.hooks:
        should_show = True
    # Show important system messages by default (errors, etc.)
    elif content and not content.startswith("[1m") and not is_hook:
        if "Error" in content or ("completed successfully" not in content):
            should_show = True

    if should_show and content:
        if metadata_lines:
            output.extend(metadata_lines)
        # Sanitize terminal output for security
        content    = sanitize_terminal_output(content, strip_all_escapes=True)
        system_msg = render("system", content=content)
        # Prepend timestamp if present
        if timestamp_str:
            output.append(timestamp_str + system_msg)
        else:
            output.append(system_msg)

    return ''.join(output) if output else None
