"""Formatting styles for claudeconvo output.

This module provides a template-based formatting system for rendering claudeconvo
messages with consistent styling. It supports:

- Template-based formatting with macro expansion
- Multiple pre-defined styles (default, compact, minimal)
- Dynamic content substitution with color support
- Terminal-aware width calculations and word wrapping
- Custom functions for advanced formatting

The system uses a simple macro language within templates:
  {{content}} - Main content substitution
  {{color}}, {{bold}}, {{reset}} - ANSI color codes
  {{name}}, {{key}}, {{value}} - Context-specific values
  {{repeat:char:width}} - Repeat character to specified width
  {{pad:width}} - Pad content to width
  {{sp:N}} - Insert N spaces
  {{nl}} - Newline character
  {{func:name:arg1:arg2}} - Call registered formatting functions

Templates are organized into styles (FormatStyle subclasses) that define
how each message type should be rendered. Each template has four fields:
  - label: Header text shown before content
  - pre_content: Separator shown before content
  - content: Main content template (applied to each line)
  - post_content: Separator shown after content

Additional template options:
  - wrap: Enable/disable word wrapping (default: see DEFAULT_WRAP_ENABLED)
  - wrap_width: Width expression for wrapping (default: see DEFAULT_WRAP_WIDTH)
"""

from __future__ import annotations

import ast
import operator
import re
import textwrap
from typing import Any, Callable, Optional, cast

from .constants import DEFAULT_FALLBACK_WIDTH, ELLIPSIS_LENGTH, MIN_WRAP_WIDTH
from .themes import Colors
from .utils import get_terminal_width, get_visual_width

# Text wrapping configuration constants
DEFAULT_WRAP_ENABLED = True     # Set to False to disable wrapping by default for all templates
DEFAULT_WRAP_WIDTH   = "terminal"  # Can be: "terminal", "terminal-N", or a specific number


def safe_eval_arithmetic(expr: str) -> float:
    """Safely evaluate arithmetic expressions without using eval().

    Only supports basic arithmetic operations: +, -, *, /, //, %, **
    and parentheses for grouping.

    Args:
        expr: String containing the arithmetic expression

    Returns:
        The evaluated result as a float

    Raises:
        ValueError: If the expression contains invalid operations
        SyntaxError: If the expression is malformed
    """
    # Define allowed operations
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node: ast.AST) -> float:
        # Handle numeric constants - works across Python versions
        # In Python 3.8+, numbers are ast.Constant nodes
        # In Python < 3.8, numbers are ast.Num nodes
        if hasattr(ast, 'Constant') and isinstance(node, ast.Constant):
            # Python 3.8+ path
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Invalid constant: {node.value!r}")
        elif hasattr(node, 'n'):
            # Handles ast.Num for Python < 3.8 without triggering deprecation warning
            # by checking for the 'n' attribute directly
            return float(node.n)
        elif isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            op_type = type(node.op)
            if op_type in ops:
                result = ops[op_type](left, right)  # type: ignore[operator]
                return float(result)
            raise ValueError(f"Unknown operator: {type(node.op).__name__}")
        elif isinstance(node, ast.UnaryOp):
            operand = evaluate(node.operand)
            op_type = type(node.op)  # type: ignore[assignment]
            if op_type in ops:
                result = ops[op_type](operand)  # type: ignore[operator]
                return float(result)
            raise ValueError(f"Unknown operator: {type(node.op).__name__}")
        else:
            raise ValueError(f"Invalid node type: {type(node).__name__}")

    try:
        tree = ast.parse(expr, mode='eval')
        if not isinstance(tree, ast.Expression):
            raise ValueError("Not a valid expression")
        return evaluate(tree.body)
    except (KeyError, TypeError) as e:
        raise ValueError(f"Invalid operation in expression: {e}")
    except RecursionError:
        raise ValueError("Expression too complex")


################################################################################

class FormatStyle:
    """Base class for formatting styles."""

    name = "default"

    # Message type templates
    # Each template has: label, pre_content, content, post_content
    # Optional: wrap (bool), wrap_width (str expression)
    templates = {
        # Conversation messages
        "user": {
            "label"        : "{{color}}{{bold}}User:{{reset}}\n",
            "pre_content"  : "",
            "content"      : " {{color}}{{content}}{{reset}}\n",
            "post_content" : "",
        },
        "assistant": {
            "label"        : "{{color}}{{bold}}Claude:{{reset}}\n",
            "pre_content"  : "",
            "content"      : " {{color}}{{content}}{{reset}}\n",
            "post_content" : "",
        },
        "system": {
            "label"        : "{{color}}System:{{reset}}\n",
            "pre_content"  : "",
            "content"      : " {{color}}{{content}}{{reset}}\n",
            "post_content" : "",
        },
        # Tool-related
        "tool_invocation": {
            "label"        : "{{color}}🔧 Tool: {{bold}}{{name}}{{reset}}\n",
            "pre_content"  : "",
            "content"      : "",
            "post_content" : "",
        },
        "tool_parameter": {
            "label"        : "",
            "pre_content"  : "",
            "content"      : "   {{color}}{{key}}: {{value}}{{reset}}\n",
            "post_content" : "",
        },
        "tool_result_success": {
            "label"        : "   {{name_color}}✓ Result:{{reset}}\n",
            "pre_content"  : "",
            "content"      : "     {{color}}{{content}}{{reset}}\n",
            "post_content" : "",
            "wrap"         : False,  # Don't wrap tool results (preserves file paths, code, etc.)
        },
        "tool_result_with_label": {
            "label"        : "   {{name_color}}✓ {{label}}{{reset}}\n",
            "pre_content"  : "",
            "content"      : "     {{color}}{{content}}{{reset}}\n",
            "post_content" : "",
            "wrap"         : False,
        },
        "tool_result_success_content": {  # For custom labels, content only
            "label"        : "",
            "pre_content"  : "",
            "content"      : "     {{color}}{{content}}{{reset}}\n",
            "post_content" : "",
            "wrap"         : False,  # Don't wrap tool results
        },
        "tool_result_error": {
            "label"        : "   {{error_color}}❌ Error:{{reset}}\n",
            "pre_content"  : "",
            "content"      : "     {{error_color}}{{content}}{{reset}}\n",
            "post_content" : "",
            "wrap"         : False,  # Don't wrap error messages
        },
        "task_result": {
            "label": "{{color}}{{bold}}{{name}} Result:{{reset}}\n",
            "pre_content": "",
            "content": "     {{color}}{{content}}{{reset}}\n",
            "post_content": "",
        },
        # Other conversation elements
        "summary": {
            "label": "{{color}}📝 Summary: {{content}}{{reset}}\n",
            "pre_content": "",
            "content": "",
            "post_content": "",
        },
        "metadata": {
            "label": "",
            "pre_content": "",
            "content": "{{color}}{{func:right_align:content}}{{reset}}\n",
            "post_content": "",
            "wrap": False,  # Disable wrapping for metadata to prevent splitting
        },
        "timestamp": {
            "label": "",
            "pre_content": "",
            "content": "{{color}}[{{content}}]{{reset}} ",  # No newline - inline with message
            "post_content": "",
        },
        # CLI output
        "error": {
            "label": "",
            "pre_content": "",
            "content": "{{error_color}}{{content}}{{reset}}",
            "post_content": "",
        },
        "warning": {
            "label": "",
            "pre_content": "",
            "content": "{{warning_color}}{{content}}{{reset}}",
            "post_content": "",
        },
        "info": {
            "label": "",
            "pre_content": "",
            "content": "{{dim}}{{content}}{{reset}}",
            "post_content": "",
        },
        "hook": {
            "label": "",
            "pre_content": "",
            "content": "{{system_color}}{{content}}{{reset}}\n",
            "post_content": "",
        },
        "command": {
            "label": "",
            "pre_content": "",
            "content": "{{tool_color}}{{content}}{{reset}}\n",
            "post_content": "",
        },
        "header": {
            "label": "",
            "pre_content": "",
            "content": "{{bold}}{{content}}{{reset}}",
            "post_content": "",
        },
        "separator": {
            "label": "",
            "pre_content": "",
            "content": "{{repeat:-:terminal}}",
            "post_content": "",
            "wrap": False,  # Separators should not wrap
        },
    }


################################################################################

class BoxedStyle(FormatStyle):
    """Boxed formatting style with borders."""

    name = "boxed"

    templates = {
        **FormatStyle.templates,  # Inherit defaults
        "user": {
            "label": "\n{{bold}}USER{{reset}}\n",
            "pre_content": "┌{{repeat:─:terminal-2}}┐\n",
            "content": "│ {{color}}{{content:pad:terminal-4}}{{reset}} │\n",
            "post_content": "└{{repeat:─:terminal-2}}┘\n",
            "wrap": True,  # Enable wrapping for boxed content
            "wrap_width": "terminal-4",  # Account for box borders (│ and │ with spaces)
            "wrap_indent": "",  # No extra indent, box handles it
        },
        "assistant": {
            "label": "\n{{bold}}CLAUDE{{reset}}\n",
            "pre_content": "┌{{repeat:─:terminal-2}}┐\n",
            "content": "│ {{color}}{{content:pad:terminal-4}}{{reset}} │\n",
            "post_content": "└{{repeat:─:terminal-2}}┘\n",
            "wrap": True,
            "wrap_width": "terminal-4",
            "wrap_indent": "",
        },
    }


################################################################################

class MinimalStyle(FormatStyle):
    """Minimal formatting style."""

    name = "minimal"

    templates = {
        **FormatStyle.templates,
        "user": {
            "label": "",
            "pre_content": "",
            "content": "{{color}}> {{content}}{{reset}}\n",
            "post_content": "",
        },
        "assistant": {
            "label": "",
            "pre_content": "",
            "content": "{{color}}< {{content}}{{reset}}\n",
            "post_content": "",
        },
        "tool_invocation": {
            "label": "",
            "pre_content": "",
            "content": "{{color}}[{{name}}]{{reset}}\n",
            "post_content": "",
        },
        "tool_parameter": {
            "label": "",
            "pre_content": "",
            "content": "  {{color}}{{key}}: {{value}}{{reset}}\n",  # Simple indented format
            "post_content": "",
        },
        "tool_result_success": {
            "label": "",
            "pre_content": "",
            "content": "  {{color}}→ {{content}}{{reset}}\n",  # Simple arrow for results
            "post_content": "",
        },
        "tool_result_success_content": {
            "label": "",
            "pre_content": "",
            "content": "  {{color}}→ {{content}}{{reset}}\n",
            "post_content": "",
        },
        "tool_result_error": {
            "label": "",
            "pre_content": "",
            "content": "  {{error_color}}✗ {{content}}{{reset}}\n",  # Simple X for errors
            "post_content": "",
        },
        "metadata": {
            "label": "",
            "pre_content": "",
            "content": "  {{color}}{{content}}{{reset}}\n",  # Simple left-aligned
            "post_content": "",
            "wrap": False,
        },
        "separator": {
            "label": "",
            "pre_content": "",
            "content": "---",
            "post_content": "",
        },
    }


################################################################################

class CompactStyle(FormatStyle):
    """Compact formatting style with less whitespace."""

    name = "compact"

    templates = {
        **FormatStyle.templates,
        "user": {
            "label": "{{color}}{{bold}}U:{{reset}}",
            "pre_content": "",
            "content": " {{color}}{{content}}{{reset}}",
            "post_content": "",
        },
        "assistant": {
            "label": "{{color}}{{bold}}C:{{reset}}",
            "pre_content": "",
            "content": " {{color}}{{content}}{{reset}}",
            "post_content": "",
        },
        "tool_invocation": {
            "label": "{{color}}[{{name}}]{{reset}}",
            "pre_content": "",
            "content": "",
            "post_content": "",
        },
        "tool_parameter": {
            "label": "",
            "pre_content": "",
            "content": " {{color}}{{key}}={{value}}{{reset}}",
            "post_content": "",
        },
        "metadata": {
            "label": "",
            "pre_content": "",
            "content": " {{color}}{{content}}{{reset}}\n",  # Compact left-aligned
            "post_content": "",
            "wrap": False,
        },
    }


# Style registry
STYLES = {
    "default": FormatStyle,
    "boxed": BoxedStyle,
    "minimal": MinimalStyle,
    "compact": CompactStyle,
}

STYLE_DESCRIPTIONS = {
    "default": "Standard formatting with clear labels",
    "boxed": "Messages in boxes with borders",
    "minimal": "Minimal decorations for clean output",
    "compact": "Condensed spacing for more content",
}


# Custom formatting functions
STYLE_FUNCTIONS: dict[str, Callable] = {}


################################################################################

def register_function(name: str, func: Callable) -> None:
    """Register a custom formatting function.

    Args:
        name: Function name to use in templates
        func: Callable that returns a string
    """
    STYLE_FUNCTIONS[name] = func


################################################################################

def eval_terminal_expr(expr: str) -> int:
    """Evaluate terminal width expressions.

    Args:
        expr: Expression like 'terminal', 'terminal-4', 'terminal/2'

    Returns:
        Calculated width as integer
    """
    if expr == "terminal":
        return get_terminal_width()

    # Handle math operations
    if "terminal" in expr:
        width = get_terminal_width()
        # Replace 'terminal' with the actual width
        expr_eval = expr.replace("terminal", str(width))

        # Safely evaluate simple math expressions
        # Only allow numbers and basic operators
        if re.match(r'^[\d\s\+\-\*/\(\)]+$', expr_eval):
            try:
                # Use a safe expression evaluator instead of eval()
                result = safe_eval_arithmetic(expr_eval)
                return int(result)
            except (ValueError, SyntaxError):
                return width

    # Try to parse as integer
    try:
        return int(expr)
    except ValueError:
        return DEFAULT_FALLBACK_WIDTH  # Default fallback


################################################################################

def expand_repeat_macro(match: Any) -> str:
    """Expand repeat macros like {{repeat:char:width}}."""
    parts = match.group(1).split(':')
    if len(parts) == 3 and parts[0] == 'repeat':
        char = parts[1]
        width = eval_terminal_expr(parts[2])
        return str(char * width)
    return str(match.group(0))


################################################################################

def expand_pad_macro(text: str, width_expr: str) -> str:
    """Pad or truncate text to specified width.

    For multi-line text, pads each line individually.
    Uses visual width to properly handle emojis and wide characters.
    """
    width = eval_terminal_expr(width_expr)

    # Handle multi-line text by padding each line
    if '\n' in text:
        lines = text.split('\n')
        padded_lines = []
        for line in lines:
            visual_len = get_visual_width(line)
            if visual_len > width:
                # Truncate while accounting for visual width
                truncated = ""
                current_width = 0
                for char in line:
                    char_width = get_visual_width(char)
                    if current_width + char_width > width - ELLIPSIS_LENGTH:
                        break
                    truncated += char
                    current_width += char_width
                padded_lines.append(truncated + "...")
            else:
                # Pad with spaces to reach the target width
                padding_needed = width - visual_len
                padded_lines.append(line + ' ' * padding_needed)
        return '\n'.join(padded_lines)

    # Single line
    visual_len = get_visual_width(text)
    if visual_len > width:
        # Truncate while accounting for visual width
        truncated = ""
        current_width = 0
        for char in text:
            char_width = get_visual_width(char)
            if current_width + char_width > width - ELLIPSIS_LENGTH:
                break
            truncated += char
            current_width += char_width
        return truncated + "..."

    # Pad with spaces to reach the target width
    padding_needed = width - visual_len
    return text + ' ' * padding_needed


################################################################################

def wrap_text(text: str, width_expr: str) -> list[str]:
    """Wrap text to specified width.

    Args:
        text: Text to wrap
        width_expr: Width expression (e.g., "terminal-4", "80")

    Returns:
        List of wrapped lines
    """
    width = eval_terminal_expr(width_expr)
    if width <= 0:
        return [text]

    # Use textwrap to handle word wrapping
    wrapper = textwrap.TextWrapper(
        width=width,
        initial_indent="",
        subsequent_indent="",
        break_long_words=False,
        break_on_hyphens=False,
        expand_tabs=False,
        replace_whitespace=False,
        drop_whitespace=True,
    )

    # Handle multiple paragraphs
    paragraphs = text.split('\n')
    wrapped_lines = []

    for para in paragraphs:
        if para.strip():  # Non-empty paragraph
            wrapped = wrapper.wrap(para)
            if wrapped:
                wrapped_lines.extend(wrapped)
            else:
                # Empty after wrapping, preserve the empty line
                wrapped_lines.append("")
        else:
            # Preserve empty lines between paragraphs
            wrapped_lines.append("")

    return wrapped_lines if wrapped_lines else [text]


################################################################################

def escape_ansi_codes(text: str) -> str:
    """Escape ANSI codes in text so they display as literal characters.

    Args:
        text: Text that may contain ANSI escape codes

    Returns:
        Text with ANSI codes escaped to display literally
    """
    if not text:
        return text
    # Replace ESC character with a visible representation
    # Using <ESC> to make it clearly visible and safe
    return text.replace('\x1b', '<ESC>')


################################################################################

def expand_macros(template: str, context: dict[str, Any]) -> str:
    """Expand all macros in a template string.

    Args:
        template: Template string with macros
        context: Dictionary with values for substitution

    Returns:
        Expanded string
    """
    if not template:
        return template

    # Handle function calls {{func:name:arg1:arg2}}
    def replace_func(match: Any) -> str:
        parts = match.group(1).split(':')
        if parts[0] == 'func' and len(parts) > 1:
            func_name = parts[1]
            args = parts[2:] if len(parts) > 2 else []

            if func_name in STYLE_FUNCTIONS:
                # Resolve special arguments
                resolved_args = []
                for arg in args:
                    if arg == 'content':
                        resolved_args.append(context.get('content', ''))
                    elif arg == 'terminal':
                        resolved_args.append(get_terminal_width())
                    elif 'terminal' in arg:
                        resolved_args.append(eval_terminal_expr(arg))
                    else:
                        # Pass through any other arguments as-is
                        # This allows template authors to pass literal strings
                        resolved_args.append(arg)

                try:
                    return str(STYLE_FUNCTIONS[func_name](*resolved_args))
                except Exception:
                    return ''
        return str(match.group(0))

    template = re.sub(r'{{(func:[^}]+)}}', replace_func, template)

    # Handle repeat macros {{repeat:char:width}}
    template = re.sub(r'{{(repeat:[^}]+)}}', expand_repeat_macro, template)

    # Handle padding macros {{content:pad:width}}
    def replace_pad(match: Any) -> str:
        parts = match.group(1).split(':')
        if len(parts) == 3 and parts[1] == 'pad':
            content = context.get(parts[0], '')
            return expand_pad_macro(str(content), parts[2])
        return str(match.group(0))

    template = re.sub(r'{{(\w+:pad:[^}]+)}}', replace_pad, template)

    # Handle color and style macros
    template = template.replace('{{bold}}', str(Colors.BOLD))
    template = template.replace('{{dim}}', str(Colors.DIM))
    template = template.replace('{{reset}}', str(Colors.RESET))

    # Handle color references
    template = template.replace('{{color}}', str(context.get('color', '')))
    template = template.replace('{{name_color}}', str(Colors.TOOL_NAME))
    template = template.replace('{{error_color}}', str(Colors.ERROR))
    template = template.replace('{{warning_color}}', str(Colors.WARNING))
    template = template.replace('{{system_color}}', str(Colors.SYSTEM))
    template = template.replace('{{tool_color}}', str(Colors.TOOL_NAME))

    # Handle content substitutions
    for key, value in context.items():
        template = template.replace(f'{{{{{key}}}}}', str(value))

    # Handle special characters
    template = template.replace('{{nl}}', '\n')

    # Handle spaces {{sp:N}}
    def replace_spaces(match: Any) -> str:
        try:
            count = int(match.group(1))
            return ' ' * count
        except ValueError:
            return str(match.group(0))

    template = re.sub(r'{{sp:(\d+)}}', replace_spaces, template)

    return template


################################################################################

class StyleRenderer:
    """Renders content using formatting styles."""

    ################################################################################

    def __init__(self, style_name: str = "default") -> None:
        """Initialize with a specific style.

        Args:
            style_name: Name of the style to use
        """
        style_class = STYLES.get(style_name, FormatStyle)
        self.style = style_class()

    ################################################################################

    def render(
        self,
        msg_type : str,
        content  : str = "",
        context  : Optional[dict[str, Any]] = None,
        **kwargs: Any
    ) -> str:
        """Render content using the style templates.

        Args:
            msg_type: Type of message (user, assistant, tool_invocation, etc.)
            content: Main content to render
            context: Additional context for macro expansion
            **kwargs: Additional keyword arguments added to context

        Returns:
            Formatted string
        """
        if msg_type not in self.style.templates:
            # Fallback to plain text if template not found
            return content

        template: dict[str, Any] = cast(dict[str, Any], self.style.templates[msg_type])

        # Build context
        full_context = context or {}
        full_context.update(kwargs)  # Add any kwargs to context
        # Escape any ANSI codes in the content so they display literally
        full_context['content'] = escape_ansi_codes(content) if content else content

        # Set default color based on message type
        if 'color' not in full_context:
            color_map = {
                'user': Colors.USER,
                'assistant': Colors.ASSISTANT,
                'system': Colors.SYSTEM,
                'tool_invocation': Colors.TOOL_NAME,
                'tool_parameter': Colors.TOOL_PARAM,
                'tool_result_success': Colors.TOOL_OUTPUT,
                'tool_result_success_content': Colors.TOOL_OUTPUT,
                'tool_result_with_label': Colors.TOOL_OUTPUT,
                'tool_result_error': Colors.ERROR,
                'task_result': Colors.TOOL_NAME,
                'summary': Colors.SEPARATOR,
                'metadata': Colors.METADATA,
                'timestamp': Colors.TIMESTAMP,
                'error': Colors.ERROR,
                'warning': Colors.WARNING,
                'info': Colors.DIM,
                'header': Colors.BOLD,
            }
            full_context['color'] = color_map.get(msg_type, '')

        # Build output
        output: list[str] = []

        # Add label if present
        if template.get('label'):
            label = expand_macros(template['label'], full_context)
            if label:
                output.append(label)

        # Add pre-content separator
        if template.get('pre_content'):
            pre = expand_macros(template['pre_content'], full_context)
            if pre:
                output.append(pre)

        # Add content (handle multi-line and wrapping)
        if template.get('content'):
            content_template = template['content']
            if content:  # If there's actual content, process it
                # Check if wrapping is enabled
                if template.get('wrap', DEFAULT_WRAP_ENABLED):
                    # Calculate the fixed prefix length from the content template
                    # For templates with padding, we need to calculate the actual
                    # prefix/suffix characters, not the padded width
                    # Replace content:pad macros with just the content to get true prefix
                    import re
                    test_template = re.sub(
                        r'\{\{content:pad:[^}]+\}\}', '{{content}}', content_template
                    )
                    temp_context = full_context.copy()
                    temp_context['content'] = ''
                    prefix = expand_macros(test_template, temp_context)
                    # Remove ANSI codes to get actual display length
                    clean_prefix = re.sub(r'\x1b\[[0-9;]*m', '', prefix)
                    prefix_len = len(clean_prefix)

                    # Get wrap settings
                    wrap_width_expr = template.get('wrap_width', DEFAULT_WRAP_WIDTH)
                    base_width = eval_terminal_expr(wrap_width_expr)

                    # Auto-adjust width for the prefix
                    actual_wrap_width = base_width - prefix_len
                    if actual_wrap_width < MIN_WRAP_WIDTH:  # Minimum reasonable width
                        actual_wrap_width = MIN_WRAP_WIDTH

                    # Escape ANSI codes BEFORE wrapping so the wrapper
                    # accounts for actual display width
                    escaped_content = escape_ansi_codes(content)

                    # Wrap the escaped content at the adjusted width (no separate indent needed)
                    wrapped_lines = wrap_text(escaped_content, str(actual_wrap_width))

                    # Render each wrapped line
                    for line in wrapped_lines:
                        # Content is already escaped, use it directly
                        full_context['content'] = line
                        # Use the same template for all lines
                        # The wrapping already handles indentation
                        rendered = expand_macros(content_template, full_context)
                        if rendered:
                            output.append(rendered)
                else:
                    # No wrapping, process line by line as before
                    lines = content.split('\n')
                    for line in lines:
                        # Escape ANSI codes in each line
                        full_context['content'] = escape_ansi_codes(line)
                        rendered = expand_macros(content_template, full_context)
                        if rendered:
                            output.append(rendered)
            else:  # No content, but template might use other context values
                rendered = expand_macros(content_template, full_context)
                if rendered and rendered.strip():  # Only add if not just whitespace
                    output.append(rendered)

        # Add post-content separator if defined
        if 'post_content' in template:
            post = expand_macros(template['post_content'], full_context)
            if post:  # Only append if there's actual content
                output.append(post)

        return ''.join(output)

    ################################################################################

    def render_inline(
        self,
        msg_type : str,
        content  : str = "",
        context  : Optional[dict[str, Any]] = None,
        **kwargs: Any
    ) -> str:
        """Render content inline (no label or separators).

        This is useful for inline formatting like errors or info messages.

        Args:
            msg_type: Type of message
            content: Content to render
            context: Additional context
            **kwargs: Additional keyword arguments added to context

        Returns:
            Formatted string
        """
        if msg_type not in self.style.templates:
            return content

        template: dict[str, Any] = cast(dict[str, Any], self.style.templates[msg_type])

        # Build context
        full_context = context or {}
        full_context.update(kwargs)  # Add any kwargs to context
        # Escape any ANSI codes in the content so they display literally
        full_context['content'] = escape_ansi_codes(content) if content else content

        # Only use the content template, skip label and separators
        if template.get('content'):
            return expand_macros(template['content'], full_context)

        return content


# Global renderer instance
_global_renderer: Optional[StyleRenderer] = None


################################################################################

def get_renderer(style_name: Optional[str] = None) -> StyleRenderer:
    """Get the global renderer instance.

    Args:
        style_name: Optional style name to set

    Returns:
        StyleRenderer instance
    """
    global _global_renderer

    if style_name or _global_renderer is None:
        _global_renderer = StyleRenderer(style_name or "default")

    return _global_renderer


################################################################################

def set_style(style_name: str) -> None:
    """Set the global formatting style.

    Args:
        style_name: Name of the style to use
    """
    get_renderer(style_name)


################################################################################

def render(msg_type: str, content: str = "", **context: Any) -> str:
    """Render content using the global style.

    Args:
        msg_type: Type of message
        content: Content to render
        **context: Additional context for macro expansion

    Returns:
        Formatted string
    """
    return get_renderer().render(msg_type, content, None, **context)


################################################################################

def render_inline(msg_type: str, content: str = "", **context: Any) -> str:
    """Render content inline using the global style.

    Args:
        msg_type: Type of message
        content: Content to render
        **context: Additional context

    Returns:
        Formatted string
    """
    return get_renderer().render_inline(msg_type, content, None, **context)


################################################################################

# Register custom formatting functions
def _right_align(content: str) -> str:
    """
    Right-align content to the terminal edge.

    Args:
        content: The content to right-align

    Returns:
        Right-aligned string with proper padding
    """
    from .utils import get_terminal_width

    # Calculate terminal width
    terminal_width = get_terminal_width()

    # Remove any existing ANSI codes from content for accurate length calculation
    import re
    clean_content = re.sub(r'\x1b\[[0-9;]*m', '', content)
    content_length = len(clean_content)

    # Calculate padding for right alignment
    # Leave 1 space at the end for visual margin
    padding_needed = max(0, terminal_width - content_length - 1)

    # Build the right-aligned string
    result = " " * padding_needed + content

    return result


def _init_style_functions() -> None:
    """Initialize built-in style functions."""
    # Register the right-align function
    register_function("right_align", _right_align)


# Initialize functions when module is imported
_init_style_functions()
