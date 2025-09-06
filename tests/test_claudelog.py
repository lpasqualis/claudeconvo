"""Tests for claudelog main functionality."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add src to path to import claudelog
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claudelog.claudelog import (
    ShowOptions,
    SessionManager,
    MessageFormatter,
    Colors,
    format_timestamp,
    wrap_text,
)


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
        assert opts.all is True
    
    def test_parse_specific_options(self):
        """Test parsing specific option flags."""
        opts = ShowOptions('sm')
        assert opts.summaries is True
        assert opts.metadata is True
        assert opts.user is False  # Not in defaults when options specified
        assert opts.assistant is False
    
    def test_uppercase_disables(self):
        """Test uppercase letters disable options."""
        opts = ShowOptions('aH')  # All except hooks
        assert opts.all is True
        assert opts.hooks is False
    
    def test_disable_all_then_enable(self):
        """Test 'A' disables all, then lowercase enables specific."""
        opts = ShowOptions('Aqw')
        assert opts.user is True
        assert opts.assistant is True
        assert opts.summaries is False
        assert opts.metadata is False


class TestMessageFormatter:
    """Test MessageFormatter class."""
    
    def test_format_user_message(self):
        """Test formatting of user messages."""
        formatter = MessageFormatter(ShowOptions('q'))
        message = {
            'role': 'user',
            'content': 'Test message'
        }
        output = formatter.format_message(message, 0)
        assert 'User:' in output
        assert 'Test message' in output
    
    def test_format_assistant_message(self):
        """Test formatting of assistant messages."""
        formatter = MessageFormatter(ShowOptions('w'))
        message = {
            'role': 'assistant',
            'content': [
                {'type': 'text', 'text': 'Response text'}
            ]
        }
        output = formatter.format_message(message, 0)
        assert 'Claude:' in output
        assert 'Response text' in output
    
    def test_format_tool_use(self):
        """Test formatting of tool use messages."""
        formatter = MessageFormatter(ShowOptions('o'))
        message = {
            'role': 'assistant',
            'content': [
                {
                    'type': 'tool_use',
                    'name': 'test_tool',
                    'input': {'param': 'value'}
                }
            ]
        }
        output = formatter.format_message(message, 0)
        assert 'Tool:' in output
        assert 'test_tool' in output
    
    def test_skip_filtered_messages(self):
        """Test that filtered message types are skipped."""
        formatter = MessageFormatter(ShowOptions('q'))  # Only user
        assistant_msg = {
            'role': 'assistant',
            'content': [{'type': 'text', 'text': 'Hidden'}]
        }
        output = formatter.format_message(assistant_msg, 0)
        assert output == ''


class TestSessionManager:
    """Test SessionManager class."""
    
    @patch('claudelog.claudelog.Path.exists')
    @patch('claudelog.claudelog.Path.iterdir')
    def test_list_sessions(self, mock_iterdir, mock_exists):
        """Test listing available sessions."""
        mock_exists.return_value = True
        
        # Create mock session files
        mock_files = [
            Mock(name='session1.json', stem='session1', 
                 stat=Mock(return_value=Mock(st_mtime=1000))),
            Mock(name='session2.json', stem='session2',
                 stat=Mock(return_value=Mock(st_mtime=2000))),
        ]
        for f in mock_files:
            f.is_file.return_value = True
            f.suffix = '.json'
        
        mock_iterdir.return_value = mock_files
        
        manager = SessionManager('/fake/path')
        sessions = manager.list_sessions()
        
        assert len(sessions) == 2
        assert sessions[0][1] == 'session2'  # Most recent first
    
    @patch('claudelog.claudelog.Path.open')
    @patch('claudelog.claudelog.Path.exists')
    def test_load_session(self, mock_exists, mock_open):
        """Test loading a session file."""
        mock_exists.return_value = True
        
        session_data = {
            'messages': [
                {'role': 'user', 'content': 'Test'}
            ]
        }
        
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = json.dumps(session_data)
        mock_open.return_value = mock_file
        
        manager = SessionManager('/fake/path')
        data = manager.load_session('test.json')
        
        assert data == session_data
        assert 'messages' in data


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        result = format_timestamp(1704067200000)  # 2024-01-01 00:00:00 UTC
        assert '2024' in result
    
    def test_format_timestamp_none(self):
        """Test timestamp formatting with None."""
        result = format_timestamp(None)
        assert result == 'No timestamp'
    
    def test_wrap_text(self):
        """Test text wrapping with indentation."""
        text = "This is a very long line that should be wrapped " * 5
        wrapped = wrap_text(text, indent=4, width=40)
        lines = wrapped.split('\n')
        
        # Check that lines are indented
        for line in lines[1:]:  # Skip first line
            if line:  # Skip empty lines
                assert line.startswith('    ')
        
        # Check that no line exceeds width (accounting for indent)
        for line in lines:
            assert len(line) <= 44  # 40 + 4 indent


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
        formatter = MessageFormatter(ShowOptions('q'))
        message = {'role': 'user', 'content': 'Test'}
        output = formatter.format_message(message, 0)
        
        # Should contain color codes
        assert Colors.USER in output
        assert Colors.RESET in output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])