"""Unit tests for the styles module."""

import unittest
from unittest.mock import Mock, patch

from claudelog.styles import (
    CompactStyle,
    FormatStyle,
    MinimalStyle,
    StyleRenderer,
    eval_terminal_expr,
    expand_macros,
    expand_pad_macro,
    expand_repeat_macro,
    get_renderer,
    register_function,
    render,
    render_inline,
    set_style,
)


class TestStyleMacros(unittest.TestCase):
    """Test macro expansion functions."""

    def test_eval_terminal_expr(self):
        """Test terminal width expression evaluation."""
        with patch("claudelog.styles.get_terminal_width", return_value=80):
            self.assertEqual(eval_terminal_expr("terminal"), 80)
            self.assertEqual(eval_terminal_expr("terminal-4"), 76)
            self.assertEqual(eval_terminal_expr("terminal+10"), 90)
            self.assertEqual(eval_terminal_expr("terminal/2"), 40)
            self.assertEqual(eval_terminal_expr("terminal*2"), 160)
            self.assertEqual(eval_terminal_expr("50"), 50)
            self.assertEqual(eval_terminal_expr("invalid"), 80)  # Fallback

    def test_expand_repeat_macro(self):
        """Test repeat macro expansion."""
        import re

        with patch("claudelog.styles.get_terminal_width", return_value=40):
            # Test simple repeat
            match = re.match(r"{{(repeat:[^}]+)}}", "{{repeat:=:10}}")
            result = expand_repeat_macro(match)
            self.assertEqual(result, "=" * 10)

            # Test with terminal expression
            match = re.match(r"{{(repeat:[^}]+)}}", "{{repeat:-:terminal}}")
            result = expand_repeat_macro(match)
            self.assertEqual(result, "-" * 40)

            # Test with terminal math
            match = re.match(r"{{(repeat:[^}]+)}}", "{{repeat:*:terminal-2}}")
            result = expand_repeat_macro(match)
            self.assertEqual(result, "*" * 38)

    def test_expand_pad_macro(self):
        """Test padding macro expansion."""
        # Test padding shorter text
        result = expand_pad_macro("hello", "10")
        self.assertEqual(result, "hello     ")
        self.assertEqual(len(result), 10)

        # Test truncating longer text
        result = expand_pad_macro("hello world", "5")
        self.assertEqual(result, "he...")
        self.assertEqual(len(result), 5)

        # Test exact length
        result = expand_pad_macro("test", "4")
        self.assertEqual(result, "test")

    def test_expand_macros(self):
        """Test full macro expansion."""
        # Mock Colors
        with patch("claudelog.styles.Colors") as mock_colors:
            mock_colors.BOLD = "[BOLD]"
            mock_colors.RESET = "[RESET]"
            mock_colors.DIM = "[DIM]"
            mock_colors.ERROR = "[ERROR]"
            mock_colors.WARNING = "[WARNING]"

            # Test simple replacements
            context = {"content": "Hello", "color": "[COLOR]"}
            result = expand_macros("{{bold}}{{content}}{{reset}}", context)
            self.assertEqual(result, "[BOLD]Hello[RESET]")

            # Test color references
            result = expand_macros("{{color}}Text{{reset}}", context)
            self.assertEqual(result, "[COLOR]Text[RESET]")

            # Test special characters
            result = expand_macros("Line1{{nl}}Line2", context)
            self.assertEqual(result, "Line1\nLine2")

            # Test spaces
            result = expand_macros("{{sp:3}}Text", context)
            self.assertEqual(result, "   Text")

            # Test repeat macros
            with patch("claudelog.styles.get_terminal_width", return_value=10):
                result = expand_macros("{{repeat:=:5}}", context)
                self.assertEqual(result, "=====")

            # Test function calls
            def test_func(arg1, arg2):
                return f"[{arg1},{arg2}]"

            register_function("test_func", test_func)
            result = expand_macros("{{func:test_func:a:b}}", context)
            self.assertEqual(result, "[a,b]")


class TestFormatStyles(unittest.TestCase):
    """Test format style classes."""

    def test_default_style(self):
        """Test default format style."""
        style = FormatStyle()
        self.assertEqual(style.name, "default")
        self.assertIn("user", style.templates)
        self.assertIn("assistant", style.templates)
        self.assertIn("tool_invocation", style.templates)

        # Check template structure
        user_template = style.templates["user"]
        self.assertIn("label", user_template)
        self.assertIn("pre_content", user_template)
        self.assertIn("content", user_template)
        self.assertIn("post_content", user_template)

    def test_minimal_style(self):
        """Test minimal format style."""
        style = MinimalStyle()
        self.assertEqual(style.name, "minimal")

        # Check that it overrides user template
        user_template = style.templates["user"]
        self.assertEqual(user_template["label"], "")
        self.assertIn(">", user_template["content"])

    def test_compact_style(self):
        """Test compact format style."""
        style = CompactStyle()
        self.assertEqual(style.name, "compact")

        # Check compact formatting
        user_template = style.templates["user"]
        self.assertIn("U:", user_template["label"])


class TestStyleRenderer(unittest.TestCase):
    """Test the StyleRenderer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock Colors
        self.color_patcher = patch("claudelog.styles.Colors")
        mock_colors = self.color_patcher.start()
        mock_colors.BOLD = "[BOLD]"
        mock_colors.RESET = "[RESET]"
        mock_colors.USER = "[USER]"
        mock_colors.ASSISTANT = "[ASSISTANT]"
        mock_colors.SYSTEM = "[SYSTEM]"
        mock_colors.TOOL_NAME = "[TOOL]"
        mock_colors.ERROR = "[ERROR]"
        mock_colors.DIM = "[DIM]"

    def tearDown(self):
        """Clean up patches."""
        self.color_patcher.stop()

    def test_renderer_initialization(self):
        """Test renderer initialization with different styles."""
        renderer = StyleRenderer()
        self.assertEqual(renderer.style.name, "default")

        renderer = StyleRenderer("minimal")
        self.assertEqual(renderer.style.name, "minimal")

        # Test invalid style falls back to default
        renderer = StyleRenderer("nonexistent")
        self.assertEqual(renderer.style.name, "default")

    def test_render_user_message(self):
        """Test rendering user messages."""
        renderer = StyleRenderer()

        result = renderer.render("user", "Hello world")
        self.assertIn("User:", result)
        self.assertIn("Hello world", result)
        self.assertIn("[USER]", result)
        self.assertIn("[BOLD]", result)

    def test_render_assistant_message(self):
        """Test rendering assistant messages."""
        renderer = StyleRenderer()

        result = renderer.render("assistant", "I can help with that")
        self.assertIn("Claude:", result)
        self.assertIn("I can help with that", result)
        self.assertIn("[ASSISTANT]", result)

    def test_render_tool_invocation(self):
        """Test rendering tool invocations."""
        renderer = StyleRenderer()

        context = {"name": "Bash"}
        result = renderer.render("tool_invocation", context=context)
        self.assertIn("Tool: Bash", result)
        self.assertIn("🔧", result)

    def test_render_with_custom_context(self):
        """Test rendering with custom context."""
        renderer = StyleRenderer()

        context = {
            "name": "TestTool",
            "key": "param1",
            "value": "value1",
            "custom": "data",
        }
        result = renderer.render("tool_parameter", context=context)
        self.assertIn("param1", result)
        self.assertIn("value1", result)

    def test_render_multiline_content(self):
        """Test rendering multiline content."""
        renderer = StyleRenderer()

        content = "Line 1\nLine 2\nLine 3"
        result = renderer.render("user", content)

        # Should process each line
        lines = result.split("\n")
        self.assertTrue(len(lines) >= 3)
        # Each content line should have color codes
        for i in range(1, 4):  # Skip the label line
            if i < len(lines):
                self.assertIn("[USER]", lines[i])

    def test_render_inline(self):
        """Test inline rendering (no label/separators)."""
        renderer = StyleRenderer()

        result = renderer.render_inline("error", "Something went wrong")
        self.assertIn("Something went wrong", result)
        self.assertIn("[ERROR]", result)
        # Should not have newlines from label
        self.assertNotIn("\n", result.strip())

    def test_render_unknown_type(self):
        """Test rendering unknown message type."""
        renderer = StyleRenderer()

        result = renderer.render("unknown_type", "Content")
        # Should fallback to just returning content
        self.assertEqual(result, "Content")


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.color_patcher = patch("claudelog.styles.Colors")
        mock_colors = self.color_patcher.start()
        mock_colors.BOLD = "[BOLD]"
        mock_colors.RESET = "[RESET]"
        mock_colors.USER = "[USER]"
        mock_colors.ERROR = "[ERROR]"

    def tearDown(self):
        """Clean up patches."""
        self.color_patcher.stop()

    def test_get_renderer(self):
        """Test getting global renderer."""
        # First call creates renderer
        renderer1 = get_renderer()
        self.assertIsNotNone(renderer1)
        self.assertEqual(renderer1.style.name, "default")

        # Second call returns same instance
        renderer2 = get_renderer()
        self.assertIs(renderer1, renderer2)

        # Can change style
        renderer3 = get_renderer("minimal")
        self.assertEqual(renderer3.style.name, "minimal")

    def test_set_style(self):
        """Test setting global style."""
        set_style("minimal")
        renderer = get_renderer()
        self.assertEqual(renderer.style.name, "minimal")

        set_style("compact")
        renderer = get_renderer()
        self.assertEqual(renderer.style.name, "compact")

    def test_render_global(self):
        """Test global render function."""
        set_style("default")
        result = render("user", "Test message")
        self.assertIn("User:", result)
        self.assertIn("Test message", result)

        # Test with additional context
        result = render("tool_invocation", name="TestTool")
        self.assertIn("TestTool", result)

    def test_render_inline_global(self):
        """Test global render_inline function."""
        set_style("default")
        result = render_inline("error", "Error message")
        self.assertIn("Error message", result)
        self.assertIn("[ERROR]", result)


class TestCustomFunctions(unittest.TestCase):
    """Test custom function registration."""

    def test_register_function(self):
        """Test registering custom functions."""
        from claudelog.styles import STYLE_FUNCTIONS

        # Clear any existing functions
        STYLE_FUNCTIONS.clear()

        # Register a custom function
        def custom_border(width):
            return "=" * int(width)

        register_function("border", custom_border)
        self.assertIn("border", STYLE_FUNCTIONS)

        # Test using the function in a template
        context = {}
        with patch("claudelog.styles.get_terminal_width", return_value=10):
            result = expand_macros("{{func:border:5}}", context)
            self.assertEqual(result, "=====")

            # Test with terminal expression
            result = expand_macros("{{func:border:terminal}}", context)
            self.assertEqual(result, "=" * 10)


class TestStyleIntegration(unittest.TestCase):
    """Integration tests for the styles system."""

    def setUp(self):
        """Set up test fixtures."""
        self.color_patcher = patch("claudelog.styles.Colors")
        mock_colors = self.color_patcher.start()
        mock_colors.BOLD = ""
        mock_colors.RESET = ""
        mock_colors.USER = ""
        mock_colors.ASSISTANT = ""
        mock_colors.ERROR = ""
        mock_colors.TOOL_NAME = ""

    def tearDown(self):
        """Clean up patches."""
        self.color_patcher.stop()

    def test_minimal_style_rendering(self):
        """Test complete rendering with minimal style."""
        set_style("minimal")

        # User message
        result = render("user", "Hello")
        self.assertEqual(result.strip(), "> Hello")

        # Assistant message
        result = render("assistant", "Hi there")
        self.assertEqual(result.strip(), "< Hi there")

        # Tool invocation
        result = render("tool_invocation", name="Bash")
        self.assertEqual(result.strip(), "[Bash]")

    def test_default_style_rendering(self):
        """Test complete rendering with default style."""
        set_style("default")

        # User message (should have label)
        result = render("user", "Test")
        self.assertIn("User:", result)
        self.assertIn("Test", result)

        # Tool parameter
        result = render("tool_parameter", key="arg", value="val")
        self.assertIn("arg:", result)
        self.assertIn("val", result)

    def test_style_switching(self):
        """Test switching between styles."""
        # Start with default
        set_style("default")
        result1 = render("user", "Test")
        self.assertIn("User:", result1)

        # Switch to minimal
        set_style("minimal")
        result2 = render("user", "Test")
        self.assertNotIn("User:", result2)
        self.assertIn(">", result2)

        # Switch to compact
        set_style("compact")
        result3 = render("user", "Test")
        self.assertIn("U:", result3)


if __name__ == "__main__":
    unittest.main()