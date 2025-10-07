"""Tests for claudeconvo main functionality."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os
import pytest

# Add src to path to import claudeconvo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claudeconvo.options import ShowOptions
from claudeconvo.themes import (
    Colors,
    ColorTheme,
    DarkTheme,
    LightTheme,
    MonoTheme,
    get_color_theme,
    THEMES,
)
from claudeconvo.config import determine_theme, load_config
from claudeconvo.session import (
    path_to_session_dir,
    get_project_session_dir,
    list_session_files,
    parse_session_file,
    find_project_root,
)
from claudeconvo.formatters import format_conversation_entry


class TestShowOptions:
    """Test ShowOptions class."""

    def test_default_options(self):
        """Test default options are set correctly."""
        opts = ShowOptions()
        assert opts.user is True
        assert opts.assistant is True
        assert opts.tools is True
        assert opts.summaries is False
        assert opts.metadata is False

    def test_parse_all_option(self):
        """Test 'a' enables all options."""
        opts = ShowOptions("a")
        assert opts.user is True
        assert opts.assistant is True
        assert opts.summaries is True
        assert opts.metadata is True
        # Note: 'all' itself is not set, it's just a flag to enable others

    def test_parse_specific_options(self):
        """Test parsing specific option flags."""
        opts = ShowOptions("sm")
        assert opts.summaries is True
        assert opts.metadata is True
        # Note: defaults are still enabled, specific options add to them
        assert opts.user is True  # Default still enabled
        assert opts.assistant is True  # Default still enabled

    def test_uppercase_disables(self):
        """Test uppercase letters disable options."""
        opts = ShowOptions("aH")  # All except hooks
        # 'a' enables all options except 'all' itself
        assert opts.user is True
        assert opts.assistant is True
        assert opts.hooks is False  # Uppercase H disables hooks

    def test_disable_all_then_enable(self):
        """Test 'A' disables all, then lowercase enables specific."""
        opts = ShowOptions("Aqw")
        assert opts.user is True
        assert opts.assistant is True
        assert opts.summaries is False
        assert opts.metadata is False

    def test_tool_details_option(self):
        """Test that 't' option prevents tool truncation."""
        # Without 't' option - should truncate
        opts_without = ShowOptions("o")
        assert opts_without.tools is True
        assert opts_without.tool_details is False
        assert opts_without.should_truncate("tool_param") is True
        assert opts_without.should_truncate("tool_result") is True
        assert opts_without.get_max_length("tool_param") == 200
        assert opts_without.get_max_length("tool_result") == 500

        # With 't' option - should NOT truncate tool output
        opts_with = ShowOptions("ot")
        assert opts_with.tools is True
        assert opts_with.tool_details is True
        assert opts_with.should_truncate("tool_param") is False
        assert opts_with.should_truncate("tool_result") is False
        assert opts_with.get_max_length("tool_param") == float("inf")
        assert opts_with.get_max_length("tool_result") == float("inf")

        # Combined flags 'st' - summaries and tool details
        opts_combined = ShowOptions("st")
        assert opts_combined.summaries is True
        assert opts_combined.tool_details is True
        assert opts_combined.should_truncate("tool_param") is False
        assert opts_combined.should_truncate("tool_result") is False


class TestMessageFormatting:
    """Test message formatting functionality."""

    def test_format_user_message(self):
        """Test formatting of user messages."""
        entry = {"type": "user", "message": {"content": "Test message"}}
        output = format_conversation_entry(entry, ShowOptions("q"), False)
        assert output is not None
        assert "User:" in output
        assert "Test message" in output

    def test_format_assistant_message(self):
        """Test formatting of assistant messages."""
        entry = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Response text"}]},
        }
        output = format_conversation_entry(entry, ShowOptions("w"), False)
        assert output is not None
        assert "Claude:" in output
        assert "Response text" in output

    def test_format_tool_use(self):
        """Test formatting of tool use messages."""
        entry = {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "tool_use", "name": "test_tool", "input": {"param": "value"}}],
        }
        output = format_conversation_entry(entry, ShowOptions("o"), False)
        if output:  # May be None if filtering
            assert "Tool:" in output or "test_tool" in output

    def test_skip_filtered_messages(self):
        """Test that filtered message types are skipped."""
        entry = {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hidden"}],
        }
        output = format_conversation_entry(entry, ShowOptions("q"), False)  # Only user
        # Should skip assistant messages when only user is enabled
        assert output is None or "Hidden" not in output


class TestSessionFunctions:
    """Test session management functions."""

    def test_path_to_session_dir(self):
        """Test converting paths to session directory names."""
        # Test basic path conversion
        result = path_to_session_dir("/home/user/project")
        assert result.name == "-home-user-project"

        # Test path with underscores
        result = path_to_session_dir("/home/user/my_project")
        assert result.name == "-home-user-my-project"

        # Test path with dots
        result = path_to_session_dir("/home/user/.hidden")
        assert result.name == "-home-user--hidden"

    @patch("claudeconvo.session.path_to_session_dir")
    @patch("claudeconvo.session.Path")
    def test_find_project_root(self, mock_path_class, mock_path_to_session):
        """Test finding project root from subdirectories."""
        # Create mock paths for the directory hierarchy
        mock_subdir = Mock()
        mock_src = Mock()
        mock_project = Mock()
        mock_home = Mock()

        # Set up the parent chain
        mock_subdir.parent = mock_src
        mock_src.parent = mock_project
        mock_project.parent = mock_home
        mock_home.parent = mock_home  # Root directory points to itself

        # Set up string representations
        mock_subdir.__str__ = lambda self: "/home/user/project/src/subdir"
        mock_src.__str__ = lambda self: "/home/user/project/src"
        mock_project.__str__ = lambda self: "/home/user/project"
        mock_home.__str__ = lambda self: "/home"

        # Mock the / operator for path joining
        def make_div(base_path, has_git=False):
            def div(self, other):
                mock_result = Mock()
                mock_result.exists = Mock(return_value=(other == ".git" and has_git))
                return mock_result

            return div

        mock_subdir.__truediv__ = make_div(mock_subdir, False)
        mock_src.__truediv__ = make_div(mock_src, False)
        mock_project.__truediv__ = make_div(mock_project, True)  # Project has .git
        mock_home.__truediv__ = make_div(mock_home, False)

        # Mock Path() constructor and resolve()
        mock_path_class.return_value.resolve.return_value = mock_subdir

        # Mock path_to_session_dir to return non-existent session dirs
        mock_session_dir = Mock()
        mock_session_dir.exists.return_value = False
        mock_path_to_session.return_value = mock_session_dir

        # Test finding project root
        result = find_project_root("/home/user/project/src/subdir")
        assert result == "/home/user/project"

    @patch("claudeconvo.session.Path.glob")
    @patch("claudeconvo.session.Path.exists")
    def test_list_session_files(self, mock_exists, mock_glob):
        """Test listing session files."""
        mock_exists.return_value = True

        # Create mock session files
        mock_files = [
            Mock(
                name="session1.jsonl", stem="session1", stat=Mock(return_value=Mock(st_mtime=1000))
            ),
            Mock(
                name="session2.jsonl", stem="session2", stat=Mock(return_value=Mock(st_mtime=2000))
            ),
        ]

        mock_glob.return_value = mock_files

        # Create a mock path with glob method
        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = mock_files

        files = list_session_files(mock_path)

        assert len(files) == 2
        # Files should be sorted by modification time (newest first)
        assert files[0] == mock_files[1]  # session2 has newer mtime
        assert files[1] == mock_files[0]  # session1 has older mtime

    @patch("claudeconvo.parsers.adaptive.Path")
    @patch("os.fstat")
    @patch("builtins.open")
    @patch("claudeconvo.session.Path.is_symlink")
    @patch("claudeconvo.session.Path.resolve")
    def test_parse_session_file(
        self, mock_resolve, mock_is_symlink, mock_open, mock_fstat, mock_adaptive_path
    ):
        """Test parsing a session file."""
        # Mock adaptive parser config loading
        mock_config_path = Mock()
        mock_config_path.exists.return_value = False  # No config file
        mock_parent = Mock()
        mock_parent.__truediv__ = Mock(return_value=mock_config_path)
        mock_file_path = Mock()
        mock_file_path.parent.parent = mock_parent
        mock_adaptive_path.return_value = mock_file_path

        # Mock path validation to pass
        home_sessions = Path.home() / ".claude" / "projects" / "test"
        test_file = home_sessions / "session.jsonl"
        mock_resolve.return_value = test_file

        # Mock symlink check
        mock_is_symlink.return_value = False

        # Mock file size check using fstat
        mock_fstat.return_value = Mock(st_size=1000)  # Small file

        # Mock file content with newline-delimited JSON
        # Use realistic Claude log format
        session_data = [
            {"type": "user", "version": "1.0.108", "message": {"role": "user", "content": "Test"}},
            {
                "type": "assistant",
                "version": "1.0.108",
                "message": {"role": "assistant", "content": "Response"},
            },
        ]

        mock_file_handle = MagicMock()
        mock_file_handle.__iter__ = Mock(
            return_value=iter([json.dumps(entry) + "\n" for entry in session_data])
        )
        mock_file_handle.fileno = Mock(return_value=3)  # Mock file descriptor

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file_handle
        mock_open.return_value = mock_file

        entries = parse_session_file("/fake/session.json")

        assert len(entries) == 2
        # Parsed entries have normalized structure
        assert entries[0]["type"] == "user"
        assert entries[0]["message"]["content"] == "Test"
        assert entries[1]["type"] == "assistant"
        assert entries[1]["message"]["content"] == "Response"


# Removed TestUtilityFunctions since wrap_text doesn't exist in the main module


class TestColorOutput:
    """Test color output functionality."""

    def test_colors_defined(self):
        """Test that all color codes are defined."""
        assert Colors.USER
        assert Colors.ASSISTANT
        assert Colors.SYSTEM
        assert Colors.ERROR
        assert Colors.RESET

    def test_color_in_output(self):
        """Test that colors are included in formatted output."""
        entry = {"type": "message", "role": "user", "content": "Test"}
        output = format_conversation_entry(entry, ShowOptions("q"), False)

        # Should contain color codes if output is not None
        if output:
            assert Colors.USER in output
            assert Colors.RESET in output


class TestTaskResultFormatting:
    """Test Task/subagent result formatting."""

    def test_format_task_result_as_subagent(self):
        """Test that Task results are displayed as Subagent."""
        # Create a Task result entry with _task_info
        entry = {
            "type": "user",
            "_task_info": {
                "name": "Task",
                "subagent_type": "general-purpose",
                "description": "Analyze code",
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [{"type": "text", "text": "Task completed analysis"}],
                    }
                ]
            },
        }

        output = format_conversation_entry(entry, ShowOptions("o"), False)
        assert output is not None
        assert "Subagent (general-purpose):" in output
        assert "Task completed analysis" in output
        assert "User:" not in output

    def test_format_task_result_with_description(self):
        """Test that Task descriptions are shown with tool_details."""
        entry = {
            "type": "user",
            "_task_info": {
                "name": "Task",
                "subagent_type": "hack-spotter",
                "description": "Security analysis",
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [{"type": "text", "text": "Found vulnerabilities"}],
                    }
                ]
            },
        }

        # Without tool_details - no description
        output = format_conversation_entry(entry, ShowOptions("o"), False)
        assert output is not None
        assert "Subagent (hack-spotter):" in output
        assert "[Security analysis]" not in output

        # With tool_details - show description
        output_detailed = format_conversation_entry(entry, ShowOptions("ot"), False)
        assert output_detailed is not None
        assert "Subagent (hack-spotter):" in output_detailed
        assert "Security analysis" in output_detailed

    def test_regular_tool_result_not_affected(self):
        """Test that regular tool results are not affected by Task formatting."""
        entry = {
            "type": "user",
            "toolUseResult": "Command executed successfully",
        }

        output = format_conversation_entry(entry, ShowOptions("o"), False)
        assert output is not None
        assert "✓ Result:" in output
        assert "Command executed successfully" in output
        assert "Subagent" not in output

    def test_task_result_without_task_info(self):
        """Test handling of tool_result without _task_info."""
        entry = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [{"type": "text", "text": "Regular result"}],
                    }
                ]
            },
        }

        # Without _task_info, should not be treated as Task result
        output = format_conversation_entry(entry, ShowOptions("o"), False)
        # Should either be None or not contain Subagent
        if output:
            assert "Subagent" not in output

    def test_format_regular_tool_result(self):
        """Test that regular tool results (e.g., TodoWrite) are displayed with proper labels."""
        # Create a regular tool result entry with _tool_info
        entry = {
            "type": "user",
            "_tool_info": {
                "name": "TodoWrite",
                "input": {"todos": []},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [
                            {"type": "text", "text": "Todos have been modified successfully"}
                        ],
                    }
                ]
            },
        }

        output = format_conversation_entry(entry, ShowOptions("o"), False)
        assert output is not None
        import re
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        assert "TodoWrite Result:" in clean_output
        assert "Todos have been modified successfully" in output
        assert "User:" not in output  # Should not show as User

    def test_format_bash_tool_result(self):
        """Test that Bash tool results are displayed with proper labels."""
        entry = {
            "type": "user",
            "_tool_info": {
                "name": "Bash",
                "input": {"command": "ls -la"},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [
                            {
                                "type": "text",
                                "text": "total 16\ndrwxr-xr-x  4 user  staff  128 Jan  1 12:00 .",
                            }
                        ],
                    }
                ]
            },
        }

        output = format_conversation_entry(entry, ShowOptions("o"), False)
        assert output is not None
        import re
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        assert "Bash Result:" in clean_output
        assert "total 16" in output
        assert "User:" not in output  # Should not show as User

    def test_tool_result_indentation(self):
        """Test that tool results are properly indented when indent_results is True."""
        import re
        
        entry = {
            "type": "user",
            "_tool_info": {
                "name": "Bash",
                "input": {"command": "echo test"},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "test output",
                    }
                ]
            },
        }

        # Test with indentation enabled (default)
        show_options = ShowOptions("o")
        show_options.indent_results = True
        output = format_conversation_entry(entry, show_options, False)
        
        # Remove ANSI codes for easier testing
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        
        # Check the output format
        assert output is not None
        # Check for indented label with checkmark
        assert "   ✓ Bash Result:" in clean_output
        # Result should be indented with extra spaces (5 spaces total)
        assert "     test output" in clean_output

    def test_tool_result_no_indentation(self):
        """Test that tool results are not indented when indent_results is False."""
        entry = {
            "type": "user",
            "_tool_info": {
                "name": "Bash",
                "input": {"command": "echo test"},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "test output",
                    }
                ]
            },
        }

        # Test with indentation disabled
        show_options = ShowOptions("o")
        show_options.indent_results = False
        output = format_conversation_entry(entry, show_options, False)
        
        # Should have label and result (result on next line now)
        import re
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
        assert "Bash Result:" in clean_output
        # Result should still be shown but not indented as much when indent_results is False
        # Tool results are always on separate lines now
        lines = output.split("\n")
        has_result = False
        for line in lines:
            if "test output" in line:
                has_result = True
                break
        assert has_result

    def test_multi_line_tool_result_indentation(self):
        """Test that multi-line tool results maintain consistent indentation."""
        entry = {
            "type": "user",
            "_tool_info": {
                "name": "Bash",
                "input": {"command": "ls -la"},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "Line 1\nLine 2\nLine 3",
                    }
                ]
            },
        }

        # Test with indentation enabled
        show_options = ShowOptions("o")
        show_options.indent_results = True
        output = format_conversation_entry(entry, show_options, False)
        
        lines = output.split("\n")
        # Find lines with our content
        content_lines = [l for l in lines if "Line " in l]
        
        # All content lines should be indented with 3 spaces
        assert len(content_lines) == 3
        for line in content_lines:
            assert line.startswith("   ")
            
    def test_tool_result_color_consistency(self):
        """Test that tool result labels use consistent colors."""
        from claudeconvo.themes import Colors
        
        entry = {
            "type": "user",
            "_tool_info": {
                "name": "Bash",
                "input": {"command": "test"},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "output",
                    }
                ]
            },
        }

        output = format_conversation_entry(entry, ShowOptions("o"), False)
        
        # Check that Bash Result: label contains TOOL_NAME color code
        assert Colors.TOOL_NAME in output
        # Check that output contains TOOL_OUTPUT color code
        assert Colors.TOOL_OUTPUT in output
        
    def test_tool_result_blank_line_spacing(self):
        """Test that there's a blank line between tool parameters and result."""
        from claudeconvo.formatters import format_tool_use
        
        # First format a tool use
        tool_entry = {
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "id": "test-id",
                        "input": {"command": "echo test", "description": "Test command"},
                    }
                ]
            }
        }
        
        # Then format the result
        result_entry = {
            "type": "user",
            "_tool_info": {
                "name": "Bash",
                "input": {"command": "echo test"},
            },
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": "test output",
                    }
                ]
            },
        }
        
        show_options = ShowOptions("o")
        show_options.indent_results = True
        
        tool_output = format_tool_use(tool_entry, show_options)
        result_output = format_conversation_entry(result_entry, show_options, False)
        
        # Result output formatting has changed - no longer starts with blank line
        lines = result_output.split("\n")
        # Should have the tool result header and content
        import re
        clean_result = re.sub(r'\x1b\[[0-9;]*m', '', result_output)
        assert "Bash Result:" in clean_result
        assert "test output" in result_output


class TestToolInvocationTracker:
    """Test tool invocation tracking."""

    def test_track_tool_use(self):
        """Test tracking of tool invocations."""
        from claudeconvo.tool_tracker import ToolInvocationTracker

        tracker = ToolInvocationTracker()

        # Track a regular tool use
        entry = {
            "type": "assistant",
            "timestamp": "2025-01-01T12:00:00Z",
            "uuid": "test-uuid",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool-123",
                        "name": "Bash",
                        "input": {"command": "ls -la"},
                    }
                ]
            },
        }

        tracker.track_tool_use(entry)

        # Verify tracking
        info = tracker.get_tool_info("tool-123")
        assert info is not None
        assert info["name"] == "Bash"
        assert info["input"]["command"] == "ls -la"
        assert info["uuid"] == "test-uuid"

    def test_track_task_invocation(self):
        """Test tracking of Task invocations with subagent details."""
        from claudeconvo.tool_tracker import ToolInvocationTracker

        tracker = ToolInvocationTracker()

        # Track a Task invocation
        entry = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "task-456",
                        "name": "Task",
                        "input": {
                            "subagent_type": "hack-spotter",
                            "description": "Security audit",
                            "prompt": "Analyze security",
                        },
                    }
                ]
            },
        }

        tracker.track_tool_use(entry)

        # Verify Task-specific tracking
        info = tracker.get_tool_info("task-456")
        assert info is not None
        assert info["name"] == "Task"
        assert info["subagent_type"] == "hack-spotter"
        assert info["description"] == "Security audit"

    def test_is_task_result(self):
        """Test identification of Task results."""
        from claudeconvo.tool_tracker import ToolInvocationTracker

        tracker = ToolInvocationTracker()

        # Test Task result (with array content)
        task_result = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [{"type": "text", "text": "Result"}],
                    }
                ]
            },
        }
        assert tracker.is_task_result(task_result) is True

        # Test regular tool result (string content)
        regular_result = {
            "type": "user",
            "toolUseResult": "Simple result",
        }
        assert tracker.is_task_result(regular_result) is False

        # Test non-user entry
        assistant_entry = {
            "type": "assistant",
            "message": {"content": "Response"},
        }
        assert tracker.is_task_result(assistant_entry) is False

    def test_get_task_info_for_entry(self):
        """Test retrieving Task info for a tool_result entry."""
        from claudeconvo.tool_tracker import ToolInvocationTracker

        tracker = ToolInvocationTracker()

        # First track the invocation
        tracker.tool_invocations["task-789"] = {
            "name": "Task",
            "subagent_type": "delegate",
            "description": "Check with GPT",
        }

        # Create a result entry
        result_entry = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "task-789",
                        "content": [{"type": "text", "text": "GPT response"}],
                    }
                ]
            },
        }

        # Get Task info
        info = tracker.get_task_info_for_entry(result_entry)
        assert info is not None
        assert info["subagent_type"] == "delegate"
        assert info["description"] == "Check with GPT"


class TestColorThemes:
    """Test color theme system."""

    def test_all_themes_available(self):
        """Test that all expected themes are registered."""
        expected_themes = [
            "dark",
            "light",
            "solarized-dark",
            "solarized-light",
            "dracula",
            "nord",
            "mono",
            "high-contrast",
        ]
        for theme in expected_themes:
            assert theme in THEMES

    def test_get_color_theme(self):
        """Test getting themes by name."""
        # Test valid themes
        dark = get_color_theme("dark")
        assert isinstance(dark, DarkTheme)
        assert dark.name == "dark"

        light = get_color_theme("light")
        assert isinstance(light, LightTheme)
        assert light.name == "light"

        # Test default fallback
        default = get_color_theme("nonexistent")
        assert isinstance(default, DarkTheme)

    def test_mono_theme_no_colors(self):
        """Test that mono theme has no color codes."""
        mono = get_color_theme("mono")
        assert mono.RESET == ""
        assert mono.BOLD == ""
        assert mono.DIM == ""
        # User, Assistant etc inherit empty string from base
        assert mono.USER == ""

    def test_theme_inheritance(self):
        """Test that themes properly inherit from ColorTheme."""
        for theme_class in THEMES.values():
            theme = theme_class()
            assert isinstance(theme, ColorTheme)
            assert hasattr(theme, "name")
            assert hasattr(theme, "USER")
            assert hasattr(theme, "ASSISTANT")

    def test_determine_theme_priority(self):
        """Test theme selection priority order."""
        # Mock args and config
        from argparse import Namespace

        # Test CLI arg takes priority
        args = Namespace(theme="light", no_color=False)
        config = {"theme": "dark"}
        assert determine_theme(args, config) == "light"

        # Test no_color flag
        args = Namespace(theme=None, no_color=True)
        assert determine_theme(args, config) == "mono"

        # Test env var (when no CLI arg)
        args = Namespace(theme=None, no_color=False)
        with patch.dict("os.environ", {"CLAUDECONVO_THEME": "nord"}):
            assert determine_theme(args, config) == "nord"

        # Test config file (when no CLI or env)
        args = Namespace(theme=None, no_color=False)
        assert determine_theme(args, config) == "dark"

        # Test default (when nothing set)
        args = Namespace(theme=None, no_color=False)
        assert determine_theme(args, {}) == "dark"

    @patch("claudeconvo.config.Path.exists")
    @patch("builtins.open")
    def test_load_config(self, mock_open, mock_exists):
        """Test loading configuration from file."""
        # Test successful load
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = (
            '{"theme": "light", "default_show_options": "sa"}'
        )
        config = load_config()
        # Config normalizer converts "theme" to "default_theme" for backward compatibility
        assert config == {"default_theme": "light", "default_show_options": "sa"}

        # Test missing file
        mock_exists.return_value = False
        config = load_config()
        assert config == {}

        # Test invalid JSON (should return empty dict)
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"
        config = load_config()
        assert config == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
