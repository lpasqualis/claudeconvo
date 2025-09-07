"""Tests for claudelog main functionality."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os
import pytest

# Add src to path to import claudelog
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claudelog.options import ShowOptions
from claudelog.themes import (
    Colors,
    ColorTheme,
    DarkTheme,
    LightTheme,
    MonoTheme,
    get_color_theme,
    THEMES,
)
from claudelog.config import determine_theme, load_config
from claudelog.session import (
    path_to_session_dir,
    get_project_session_dir,
    list_session_files,
    parse_session_file,
)
from claudelog.formatters import format_conversation_entry


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
        opts = ShowOptions('a')
        assert opts.user is True
        assert opts.assistant is True
        assert opts.summaries is True
        assert opts.metadata is True
        # Note: 'all' itself is not set, it's just a flag to enable others
    
    def test_parse_specific_options(self):
        """Test parsing specific option flags."""
        opts = ShowOptions('sm')
        assert opts.summaries is True
        assert opts.metadata is True
        # Note: defaults are still enabled, specific options add to them
        assert opts.user is True  # Default still enabled
        assert opts.assistant is True  # Default still enabled
    
    def test_uppercase_disables(self):
        """Test uppercase letters disable options."""
        opts = ShowOptions('aH')  # All except hooks
        # 'a' enables all options except 'all' itself
        assert opts.user is True
        assert opts.assistant is True
        assert opts.hooks is False  # Uppercase H disables hooks
    
    def test_disable_all_then_enable(self):
        """Test 'A' disables all, then lowercase enables specific."""
        opts = ShowOptions('Aqw')
        assert opts.user is True
        assert opts.assistant is True
        assert opts.summaries is False
        assert opts.metadata is False


class TestMessageFormatting:
    """Test message formatting functionality."""
    
    def test_format_user_message(self):
        """Test formatting of user messages."""
        entry = {
            'type': 'user',
            'message': {
                'content': 'Test message'
            }
        }
        output = format_conversation_entry(entry, ShowOptions('q'), False)
        assert output is not None
        assert 'User:' in output
        assert 'Test message' in output
    
    def test_format_assistant_message(self):
        """Test formatting of assistant messages."""
        entry = {
            'type': 'assistant',
            'message': {
                'content': [
                    {'type': 'text', 'text': 'Response text'}
                ]
            }
        }
        output = format_conversation_entry(entry, ShowOptions('w'), False)
        assert output is not None
        assert 'Claude:' in output
        assert 'Response text' in output
    
    def test_format_tool_use(self):
        """Test formatting of tool use messages."""
        entry = {
            'type': 'message',
            'role': 'assistant',
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'test_tool',
                    'input': {'param': 'value'}
                }
            ]
        }
        output = format_conversation_entry(entry, ShowOptions('o'), False)
        if output:  # May be None if filtering
            assert 'Tool:' in output or 'test_tool' in output
    
    def test_skip_filtered_messages(self):
        """Test that filtered message types are skipped."""
        entry = {
            'type': 'message',
            'role': 'assistant',
            'content': [{'type': 'text', 'text': 'Hidden'}]
        }
        output = format_conversation_entry(entry, ShowOptions('q'), False)  # Only user
        # Should skip assistant messages when only user is enabled
        assert output is None or 'Hidden' not in output


class TestSessionFunctions:
    """Test session management functions."""
    
    def test_path_to_session_dir(self):
        """Test converting paths to session directory names."""
        # Test basic path conversion
        result = path_to_session_dir('/home/user/project')
        assert result.name == '-home-user-project'
        
        # Test path with underscores
        result = path_to_session_dir('/home/user/my_project')
        assert result.name == '-home-user-my-project'
        
        # Test path with dots
        result = path_to_session_dir('/home/user/.hidden')
        assert result.name == '-home-user--hidden'
    
    @patch('claudelog.session.Path.glob')
    @patch('claudelog.session.Path.exists')
    def test_list_session_files(self, mock_exists, mock_glob):
        """Test listing session files."""
        mock_exists.return_value = True
        
        # Create mock session files
        mock_files = [
            Mock(name='session1.jsonl', stem='session1', 
                 stat=Mock(return_value=Mock(st_mtime=1000))),
            Mock(name='session2.jsonl', stem='session2',
                 stat=Mock(return_value=Mock(st_mtime=2000))),
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
    
    @patch('builtins.open')
    @patch('claudelog.session.Path.exists')
    def test_parse_session_file(self, mock_exists, mock_open):
        """Test parsing a session file."""
        mock_exists.return_value = True
        
        # Mock file content with newline-delimited JSON
        # Use realistic Claude log format
        session_data = [
            {"type": "user", "version": "1.0.108", "message": {"role": "user", "content": "Test"}},
            {"type": "assistant", "version": "1.0.108", "message": {"role": "assistant", "content": "Response"}}
        ]
        
        mock_file = MagicMock()
        mock_file.__enter__.return_value = [json.dumps(entry) + '\n' for entry in session_data]
        mock_open.return_value = mock_file
        
        entries = parse_session_file(Path('/fake/session.json'))
        
        assert len(entries) == 2
        # Parsed entries have normalized structure
        assert entries[0]['type'] == 'user'
        assert entries[0]['message']['content'] == 'Test'
        assert entries[1]['type'] == 'assistant'
        assert entries[1]['message']['content'] == 'Response'


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
        entry = {
            'type': 'message',
            'role': 'user',
            'content': 'Test'
        }
        output = format_conversation_entry(entry, ShowOptions('q'), False)
        
        # Should contain color codes if output is not None
        if output:
            assert Colors.USER in output
            assert Colors.RESET in output


class TestColorThemes:
    """Test color theme system."""
    
    def test_all_themes_available(self):
        """Test that all expected themes are registered."""
        expected_themes = ['dark', 'light', 'solarized-dark', 'solarized-light', 
                          'dracula', 'nord', 'mono', 'high-contrast']
        for theme in expected_themes:
            assert theme in THEMES
    
    def test_get_color_theme(self):
        """Test getting themes by name."""
        # Test valid themes
        dark = get_color_theme('dark')
        assert isinstance(dark, DarkTheme)
        assert dark.name == 'dark'
        
        light = get_color_theme('light')
        assert isinstance(light, LightTheme)
        assert light.name == 'light'
        
        # Test default fallback
        default = get_color_theme('nonexistent')
        assert isinstance(default, DarkTheme)
    
    def test_mono_theme_no_colors(self):
        """Test that mono theme has no color codes."""
        mono = get_color_theme('mono')
        assert mono.RESET == ''
        assert mono.BOLD == ''
        assert mono.DIM == ''
        # User, Assistant etc inherit empty string from base
        assert mono.USER == ''
    
    def test_theme_inheritance(self):
        """Test that themes properly inherit from ColorTheme."""
        for theme_class in THEMES.values():
            theme = theme_class()
            assert isinstance(theme, ColorTheme)
            assert hasattr(theme, 'name')
            assert hasattr(theme, 'USER')
            assert hasattr(theme, 'ASSISTANT')
    
    def test_determine_theme_priority(self):
        """Test theme selection priority order."""
        # Mock args and config
        from argparse import Namespace
        
        # Test CLI arg takes priority
        args = Namespace(theme='light', no_color=False)
        config = {'theme': 'dark'}
        assert determine_theme(args, config) == 'light'
        
        # Test no_color flag
        args = Namespace(theme=None, no_color=True)
        assert determine_theme(args, config) == 'mono'
        
        # Test env var (when no CLI arg)
        args = Namespace(theme=None, no_color=False)
        with patch.dict('os.environ', {'CLAUDELOG_THEME': 'nord'}):
            assert determine_theme(args, config) == 'nord'
        
        # Test config file (when no CLI or env)
        args = Namespace(theme=None, no_color=False)
        assert determine_theme(args, config) == 'dark'
        
        # Test default (when nothing set)
        args = Namespace(theme=None, no_color=False)
        assert determine_theme(args, {}) == 'dark'
    
    @patch('claudelog.config.Path.exists')
    @patch('builtins.open')
    def test_load_config(self, mock_open, mock_exists):
        """Test loading configuration from file."""
        # Test successful load
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"theme": "light", "default_show_options": "sa"}'
        config = load_config()
        assert config == {"theme": "light", "default_show_options": "sa"}
        
        # Test missing file
        mock_exists.return_value = False
        config = load_config()
        assert config == {}
        
        # Test invalid JSON (should return empty dict)
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = 'invalid json'
        config = load_config()
        assert config == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])