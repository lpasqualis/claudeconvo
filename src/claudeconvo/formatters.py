"""Message formatting functions for claudeconvo.

This module provides comprehensive formatting capabilities for Claude session data,
handling message display, tool execution results, and conversation presentation.
"""

import re
from datetime import datetime
from typing import Any

# Import formatting constants from constants module
from .constants import DEFAULT_MAX_LENGTH
from .parsers.adaptive import AdaptiveParser
from .styles import render, render_inline
from .utils import format_uuid, sanitize_terminal_output


def format_model_name(model_name: str) -> str:
    """Format a model name to be more readable.

    Handles various Claude model naming patterns flexibly using regex.
    Examples:
        claude-opus-4-1-20250805 -> Opus 4.1
        claude-3-sonnet -> Sonnet 3
        claude-instant -> Instant
        gpt-4 -> gpt-4 (unchanged)

    Args:
        model_name: Raw model name string

    Returns:
        Formatted model name for display
    """
    if not model_name:
        return "Unknown"

    # Handle Claude models with regex for flexibility
    import re

    # Handle different Claude model patterns
    # Pattern 1: claude-3-opus, claude-3.5-sonnet -> Opus 3, Sonnet 3.5
    pattern1 = r'^claude-(\d+(?:\.\d+)?)-([^-]+)(?:-(.+))?$'
    match1 = re.match(pattern1, model_name)

    if match1:
        version = match1.group(1)
        tier = match1.group(2).capitalize()
        return f"{tier} {version}"

    # Pattern 2: claude-opus-4-1-20250805 -> Opus 4.1
    pattern2 = r'^claude-([^-\d]+)(?:-(.+))?$'
    match2 = re.match(pattern2, model_name)

    if match2:
        tier = match2.group(1).capitalize()
        version_parts = match2.group(2)

        if version_parts:
            # Split version parts and extract numeric version
            parts = version_parts.split('-')
            version_nums = []

            for part in parts:
                # Only include numeric parts (ignore dates like 20250805)
                if part.isdigit():
                    if len(part) <= 2:  # Likely a version number
                        version_nums.append(part)
                elif '.' in part:  # Already formatted version
                    version_nums.append(part)

            if version_nums:
                version = '.'.join(version_nums)
                return f"{tier} {version}"

        return tier

    # Return original name if not a Claude model
    return model_name

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

################################################################################

def _format_tool_result_wrapped(text: str) -> str:
    """
    Format tool result text with proper wrapping and indentation.

    Args:
        text: The tool result text to format

    Returns:
        Formatted text with proper wrapping and indentation
    """
    import re
    import textwrap

    from .themes import Colors
    from .utils import get_terminal_width

    # Calculate available width
    terminal_width = get_terminal_width()
    result_indent = "     "  # 5 spaces base indent for results
    available_width = max(40, terminal_width - len(result_indent) - 4)  # Leave margin

    # Split text into lines first (preserve existing line breaks)
    lines = text.split('\n')

    # Process each line
    output_lines = []
    for line in lines:
        if not line.strip():
            # Preserve empty lines
            output_lines.append("")
            continue

        # Detect and preserve original indentation
        original_indent_match = re.match(r'^(\s*)', line)
        original_indent = original_indent_match.group(1) if original_indent_match else ""
        line_content = line[len(original_indent):]  # Content without original indent

        # Combine our result indent with the original indent
        full_indent = result_indent + original_indent

        # Check if line needs wrapping (considering the indentation)
        if len(line_content) > available_width - len(original_indent):
            # Need to wrap this line
            # For continuation lines, add extra indent for clarity
            continuation_indent = full_indent + "  "  # 2 extra spaces for wrapped lines

            # Calculate wrap width, ensuring it's positive
            wrap_width = max(20, available_width - len(original_indent))  # Minimum 20 chars

            wrapper = textwrap.TextWrapper(
                width=wrap_width,
                initial_indent="",
                subsequent_indent="",
                break_long_words=True,  # Allow breaking long words if needed
                break_on_hyphens=True,
                expand_tabs=False,
                replace_whitespace=False,
                drop_whitespace=True,
            )

            wrapped = wrapper.wrap(line_content)
            for i, wrapped_line in enumerate(wrapped):
                if i == 0:
                    # First line gets normal indent
                    output_lines.append(f"{full_indent}{Colors.TOOL_OUTPUT}{wrapped_line}{Colors.RESET}")
                else:
                    # Continuation lines get extra indent
                    output_lines.append(f"{continuation_indent}{Colors.TOOL_OUTPUT}{wrapped_line}{Colors.RESET}")
        else:
            # Line fits, just add our indent to the original
            output_lines.append(f"{full_indent}{Colors.TOOL_OUTPUT}{line_content}{Colors.RESET}")

    return '\n'.join(output_lines) + '\n'

################################################################################

def _format_tool_parameter_wrapped(
    key: str,
    value: str
) -> str:
    """
    Format a tool parameter with proper indentation and word wrapping.

    Args:
        key: Parameter name
        value: Parameter value

    Returns:
        Formatted parameter string with wrapping
    """
    import textwrap

    from .themes import Colors
    from .utils import get_terminal_width, get_visual_width

    # Calculate available width for text
    terminal_width = get_terminal_width()
    # Leave some margin for readability
    available_width = max(40, terminal_width - 4)

    # Format the parameter line
    # Using arrow notation for better visual separation with bold parameter names
    param_prefix_plain = f"→ [{key}]: "  # Plain text for width calculations
    first_line_indent = "   "  # Initial indent for parameter (3 spaces)

    # For wrapped lines, align them with the value (after the colon and space)
    # This is: 3 spaces (indent) + len("→ [") + len(key) + len("]: ")
    value_start_position = len(first_line_indent) + len(param_prefix_plain)
    continuation_indent = " " * value_start_position  # Align with value start

    # Build the full first line to check its length
    full_first_line = f"{first_line_indent}{param_prefix_plain}{value}"

    # Check the visual width (accounting for ANSI codes but not the color codes)
    first_line_visual_width = get_visual_width(full_first_line)

    # If the first line is too long, we need to wrap it
    if first_line_visual_width > available_width:
        # Calculate how much space is available for the value on the first line
        prefix_width = len(first_line_indent) + len(param_prefix_plain)
        first_line_available = available_width - prefix_width

        if first_line_available > 15:  # Only wrap if there's reasonable space
            # Calculate width for wrapped lines
            continuation_width = available_width - value_start_position

            if continuation_width > 15:  # Make sure continuation lines have space
                # Let textwrap handle all the wrapping logic properly
                # We'll format the entire "key: value" as one unit
                full_param_text = f"{param_prefix_plain}{value}"

                # Calculate available width for the first line (after indent)
                # and for continuation lines (with continuation indent)
                first_line_width = available_width - len(first_line_indent)
                continuation_line_width = available_width - len(continuation_indent)

                # Use textwrap to wrap the entire parameter text
                wrapper = textwrap.TextWrapper(
                    width=min(first_line_width, continuation_line_width),  # Use the smaller width
                    initial_indent="",
                    subsequent_indent="",
                    break_long_words=False,  # Don't break in middle of words
                    break_on_hyphens=False,  # Don't break on hyphens
                    expand_tabs=False,
                    replace_whitespace=False,  # Don't normalize newlines
                    drop_whitespace=True,
                )

                # Wrap the full parameter text, preserving line breaks
                # Split by newlines first, wrap each line, then rejoin
                input_lines = full_param_text.split('\n')
                all_wrapped = []

                for line in input_lines:
                    if line.strip():  # Non-empty line
                        wrapped = wrapper.wrap(line)
                        all_wrapped.extend(wrapped if wrapped else [line])
                    else:
                        all_wrapped.append('')  # Preserve empty lines

                wrapped_lines = all_wrapped

                if wrapped_lines:
                    # Build output with proper indentation for each line
                    output_lines = []
                    for i, line in enumerate(wrapped_lines):
                        if i == 0:
                            # First line - need to make parameter name bold
                            # Check if line starts with our prefix to apply bold to param name
                            if line.startswith(f"→ [{key}]"):
                                # Format with bold parameter name
                                bold_key = f"{Colors.BOLD}{key}{Colors.RESET}{Colors.TOOL_PARAM}"
                                formatted_line = line.replace(f"→ [{key}]", f"→ [{bold_key}]", 1)
                                output_lines.append(
                                    f"{first_line_indent}{Colors.TOOL_PARAM}"
                                    f"{formatted_line}{Colors.RESET}"
                                )
                            else:
                                # Shouldn't happen, but just in case
                                output_lines.append(
                                    f"{first_line_indent}{Colors.TOOL_PARAM}{line}{Colors.RESET}"
                                )
                        else:
                            # Continuation lines
                            output_lines.append(
                                f"{continuation_indent}{Colors.TOOL_PARAM}{line}{Colors.RESET}"
                            )

                    return '\n'.join(output_lines) + '\n'

    # If it fits on one line or can't be wrapped reasonably, just return it
    # Format with bold parameter name
    formatted_prefix = f"→ [{Colors.BOLD}{key}{Colors.RESET}{Colors.TOOL_PARAM}]: "
    return f"{first_line_indent}{Colors.TOOL_PARAM}{formatted_prefix}{value}{Colors.RESET}\n"

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
                        output.append(render("metadata", content=f"ID: {tool_id}"))

                    # Format parameters only if tool_details is enabled
                    if tool_input and show_options.tool_details:
                        max_len = show_options.get_max_length("tool_param")

                        for key, value in tool_input.items():
                            value_str = truncate_text(str(value), max_len)
                            # Format the parameter with proper indentation and wrapping
                            param_line = _format_tool_parameter_wrapped(key, value_str)
                            output.append(param_line)

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
    # Summary content can be in 'content' or 'summary' field
    summary = entry.get("content") or entry.get("summary", "N/A")
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
        # Check for model at entry level first (newer format), then in message
        model_name = entry.get("model")
        if not model_name:
            message = entry.get("message", {})
            if isinstance(message, dict):
                model_name = message.get("model")

        if model_name:
            # Format the model name to be more readable using regex for flexibility
            model_display = format_model_name(model_name)
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

    # Performance metrics
    if show_options.diagnostics:
        perf_items = []

        # Check for duration
        if "duration_ms" in entry:
            perf_items.append(f"{entry['duration_ms']}ms")
        elif "_performance" in entry and "duration_ms" in entry["_performance"]:
            perf_items.append(f"{entry['_performance']['duration_ms']}ms")

        # Check for token counts
        tokens = entry.get("tokens", {})
        if not tokens and "_performance" in entry:
            tokens = entry["_performance"]

        if isinstance(tokens, dict):
            if "input" in tokens or "tokens_in" in tokens:
                in_tokens = tokens.get("input", tokens.get("tokens_in", 0))
                perf_items.append(f"tokens-in:{in_tokens}")
            if "output" in tokens or "tokens_out" in tokens:
                out_tokens = tokens.get("output", tokens.get("tokens_out", 0))
                perf_items.append(f"tokens-out:{out_tokens}")
            if "total" in tokens:
                perf_items.append(f"tokens-total:{tokens['total']}")

        # Add performance line if we have metrics
        if perf_items:
            perf_str = f"⚡ Performance: {' | '.join(perf_items)}"
            metadata_lines.append(render("metadata", content=perf_str))

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

    elif entry_type == "hook" and show_options.hooks:
        return _format_hook_entry(entry, show_options, timestamp_str, metadata_lines)

    elif entry_type == "command" and show_options.commands:
        return _format_command_entry(entry, show_options, timestamp_str, metadata_lines)

    elif entry_type == "error" and show_options.errors:
        return _format_error_entry(entry, show_options, timestamp_str, metadata_lines)

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

    # Format the label with bold tool name
    # The label is something like "Read Result:" - make the tool name bold
    if " Result:" in label:
        tool_name_part, rest = label.split(" Result:", 1)
        bold_tool = f"{Colors.BOLD}{tool_name_part}{Colors.RESET}{Colors.TOOL_NAME}"
        formatted_label = f"{bold_tool} Result:{rest}"
    else:
        # Fallback if format is different
        formatted_label = label
    output.append(f"   {Colors.TOOL_NAME}✓ {formatted_label}{Colors.RESET}\n")

    # Format the content with proper wrapping
    wrapped_content = _format_tool_result_wrapped(text)
    output.append(wrapped_content)

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
                    # Sanitize user content to prevent terminal injection
                    sanitized_text = sanitize_terminal_output(text)
                    user_msg = render("user", content=sanitized_text)
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
            # Sanitize assistant content to prevent terminal injection
            sanitized_text = sanitize_terminal_output(text)
            assistant_msg = render("assistant", content=sanitized_text)
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


################################################################################

def _format_hook_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    timestamp_str  : str,
    metadata_lines : list[str] | None
) -> str | None:
    """Format a hook entry."""
    output = []

    hook_name = entry.get("hook_name", "unknown")
    content = entry.get("content", "")
    status = entry.get("status", "")

    if metadata_lines:
        output.extend(metadata_lines)

    hook_msg = f"🪝 Hook [{hook_name}]: {content}"
    if status:
        hook_msg += f" ({status})"

    hook_formatted = render("hook", content=hook_msg)

    if timestamp_str:
        output.append(timestamp_str + hook_formatted)
    else:
        output.append(hook_formatted)

    return ''.join(output) if output else None


################################################################################

def _format_command_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    timestamp_str  : str,
    metadata_lines : list[str] | None
) -> str | None:
    """Format a command entry."""
    output = []

    command = entry.get("command", "")
    content = entry.get("content", "")

    if metadata_lines:
        output.extend(metadata_lines)

    cmd_msg = f"⚡ Command {command}: {content}"
    cmd_formatted = render("command", content=cmd_msg)

    if timestamp_str:
        output.append(timestamp_str + cmd_formatted)
    else:
        output.append(cmd_formatted)

    return ''.join(output) if output else None


################################################################################

def _format_error_entry(
    entry          : dict[str, Any],
    show_options   : Any,
    timestamp_str  : str,
    metadata_lines : list[str] | None
) -> str | None:
    """Format an error entry."""
    output = []

    content = entry.get("content", "")
    level = entry.get("level", "error")
    details = entry.get("details", "")

    if metadata_lines:
        output.extend(metadata_lines)

    # Show error with appropriate icon
    icon = "⚠️" if level == "warning" else "❌"
    error_msg = f"{icon} {level.upper()}: {content}"

    # Add details if errors flag is enabled for extended info
    if details and show_options.errors:
        max_length = show_options.get_max_length("error")
        if len(details) > max_length:
            details = details[:int(max_length)] + "..."
        error_msg += f"\n   Details: {details}"

    error_formatted = render("error", content=error_msg)

    if timestamp_str:
        output.append(timestamp_str + error_formatted)
    else:
        output.append(error_formatted)

    return ''.join(output) if output else None
