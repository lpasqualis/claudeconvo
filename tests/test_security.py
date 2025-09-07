"""Security tests for claudelog."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import os
import pytest

# Add src to path to import claudelog
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claudelog.session import parse_session_file, find_project_root, BYTES_PER_MB
from claudelog.diagnostics import run_diagnostics
from claudelog.parsers.registry import get_parser
from claudelog.parsers.adaptive import AdaptiveParser


class TestPathSecurity:
    """Test path validation and security measures."""

    def test_parse_session_file_rejects_path_traversal(self, capsys):
        """Test that parse_session_file rejects files outside Claude sessions directory."""
        # Try to read a file outside the expected directory
        with patch("claudelog.session.Path.resolve") as mock_resolve:
            mock_resolve.return_value = Path("/etc/passwd")

            result = parse_session_file("/etc/passwd")

            assert result == []
            captured = capsys.readouterr()
            assert (
                "Security: Refusing to read file outside Claude sessions directory" in captured.err
            )

    def test_parse_session_file_accepts_valid_path(self):
        """Test that parse_session_file accepts files within Claude sessions directory."""
        home_sessions = Path.home() / ".claude" / "projects" / "test-project"
        test_file = home_sessions / "session.jsonl"

        with patch("claudelog.session.Path.resolve") as mock_resolve:
            mock_resolve.return_value = test_file
            with patch("claudelog.session.Path.is_symlink") as mock_is_symlink:
                mock_is_symlink.return_value = False
                
                # Create a proper mock file handle
                test_data_json = '{"type": "user", "content": "test"}\n'
                m = mock_open(read_data=test_data_json)
                m.return_value.fileno = Mock(return_value=3)
                
                with patch("builtins.open", m):
                    with patch("os.fstat") as mock_fstat:
                        mock_fstat.return_value = Mock(st_size=100)

                        result = parse_session_file(str(test_file))

                        # Should parse the content, not reject it
                        assert len(result) > 0

    def test_parse_session_file_rejects_large_files(self, capsys):
        """Test that parse_session_file rejects files larger than 100MB."""
        home_sessions = Path.home() / ".claude" / "projects" / "test-project"
        test_file = home_sessions / "session.jsonl"

        with patch("claudelog.session.Path.resolve") as mock_resolve:
            mock_resolve.return_value = test_file
            with patch("claudelog.session.Path.is_symlink") as mock_is_symlink:
                mock_is_symlink.return_value = False
                
                # Create a proper mock file handle  
                test_data_json = '{"type": "user", "content": "test"}\n'
                m = mock_open(read_data=test_data_json)
                m.return_value.fileno = Mock(return_value=3)
                
                with patch("builtins.open", m):
                    with patch("os.fstat") as mock_fstat:
                        # Create a file larger than 100MB
                        mock_fstat.return_value = Mock(st_size=101 * BYTES_PER_MB)

                        result = parse_session_file(str(test_file))

                        assert result == []
                        captured = capsys.readouterr()
                        assert "File too large" in captured.err
                        assert "Maximum size is 100MB" in captured.err

    def test_diagnostics_path_validation(self, capsys):
        """Test that diagnostics validates session file paths."""
        # Try to analyze a file outside the expected directory
        with patch("claudelog.diagnostics.Path.resolve") as mock_resolve:
            mock_resolve.return_value = Path("/etc/passwd")
            with patch("claudelog.diagnostics.Path.is_file") as mock_is_file:
                mock_is_file.return_value = True

                run_diagnostics(session_file="/etc/passwd")

                captured = capsys.readouterr()
                assert "Invalid session file path" in captured.out
                assert "Session files must be within" in captured.out

    def test_symlink_traversal_protection(self):
        """Test protection against symlink-based path traversal."""
        home_sessions = Path.home() / ".claude" / "projects"

        # Create a temporary directory and symlink
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            symlink = tmppath / "evil_link"
            target = Path("/etc/passwd")

            # Try to create a symlink (may fail on some systems)
            try:
                symlink.symlink_to(target)
            except OSError:
                pytest.skip("Cannot create symlinks on this system")

            with patch("claudelog.session.Path.resolve") as mock_resolve:
                # resolve() should follow symlinks and reveal the true path
                mock_resolve.return_value = target

                result = parse_session_file(str(symlink))

                assert result == []


class TestExceptionHandling:
    """Test security-conscious exception handling."""

    def test_adaptive_parser_config_error_logging(self, capsys):
        """Test that parser config errors are logged without exposing sensitive details."""
        with patch("builtins.open", mock_open(read_data='{"invalid json')):
            with patch("pathlib.Path.exists", return_value=True):
                # Enable debug mode for this test
                with patch.dict(os.environ, {"CLAUDELOG_DEBUG": "1"}):
                    parser = AdaptiveParser(config_path="test_config.json")

                    captured = capsys.readouterr()
                    assert "[DEBUG] Failed to load config from" in captured.err
                    # The error message should be included (could be JSONDecodeError or the actual error message)
                    assert "Unterminated string" in captured.err or "JSONDecodeError" in captured.err

    def test_session_parser_error_sanitization(self, capsys):
        """Test that parser errors don't expose full error details."""
        test_data = '{"type": "test", "content": "data"}\n'

        with patch("claudelog.session.Path.resolve") as mock_resolve:
            home_sessions = Path.home() / ".claude" / "projects" / "test"
            mock_resolve.return_value = home_sessions / "session.jsonl"
            
            with patch("claudelog.session.Path.is_symlink") as mock_is_symlink:
                mock_is_symlink.return_value = False
                
                # Create a proper mock file handle
                m = mock_open(read_data=test_data)
                m.return_value.fileno = Mock(return_value=3)
                
                with patch("builtins.open", m):
                    with patch("os.fstat") as mock_fstat:
                        mock_fstat.return_value = Mock(st_size=100)

                        # Mock the parser to raise an error
                        with patch(
                            "claudelog.parsers.adaptive.AdaptiveParser.parse_entry"
                        ) as mock_parse:
                            mock_parse.side_effect = ValueError("Sensitive error details")

                            result = parse_session_file("test.jsonl")

                            captured = capsys.readouterr()
                            # Should show error type but not the actual message
                            assert "ValueError" in captured.err
                            assert "Sensitive error details" not in captured.err

                        # Result should include raw data with sanitized error flag
                        assert len(result) == 1
                        assert result[0]["_parse_error"] == "ValueError"


class TestInputValidation:
    """Test input validation for security."""

    def test_parser_registry_validates_entry_type(self):
        """Test that get_parser validates entry parameter type."""
        with pytest.raises(TypeError) as excinfo:
            get_parser(entry="not a dict")

        assert "Entry must be a dictionary" in str(excinfo.value)

    def test_parser_registry_accepts_none_entry(self):
        """Test that get_parser accepts None as entry."""
        # Should not raise an error
        parser = get_parser(entry=None)
        assert parser is not None

    def test_parser_registry_accepts_dict_entry(self):
        """Test that get_parser accepts dictionary entry."""
        # Should not raise an error
        parser = get_parser(entry={"version": "1.0.80"})
        assert parser is not None


class TestRecursionLimits:
    """Test recursion depth limits to prevent stack overflow."""

    def test_content_extraction_recursion_limit(self):
        """Test that content extraction has recursion depth limits."""
        parser = AdaptiveParser()

        # Create deeply nested content
        content = {"text": "base"}
        for _ in range(30):  # Create nesting deeper than the limit
            content = {"content": content}

        result = parser._extract_text_from_content(content)

        # Should return a truncation message instead of causing stack overflow
        assert result == "[Content too deeply nested]"

    def test_content_extraction_normal_depth(self):
        """Test that normal depth content is extracted correctly."""
        parser = AdaptiveParser()

        # Create moderately nested content (within limits)
        content = {"content": {"text": {"value": "This is the actual text"}}}

        result = parser._extract_text_from_content(content)

        # Should extract the text normally
        assert result == "This is the actual text"


class TestResourceLimits:
    """Test resource limits to prevent DoS attacks."""

    def test_file_size_limit_enforcement(self):
        """Test that file size limits are enforced."""
        # Already tested in test_parse_session_file_rejects_large_files
        pass

    def test_json_serialization_error_handling(self):
        """Test that JSON serialization errors are caught properly."""
        parser = AdaptiveParser()

        # Create an object that can't be serialized
        class UnserializableObject:
            def __repr__(self):
                raise Exception("Cannot serialize")

        # Create content with unserializable object
        content = {"obj": UnserializableObject()}

        # Mock json.dumps to raise specific errors
        with patch("json.dumps") as mock_dumps:
            mock_dumps.side_effect = RecursionError("Max recursion")

            result = parser._extract_text_from_content(content)

            # Should handle the error gracefully
            assert result is None


class TestPathTraversalInFindProjectRoot:
    """Test find_project_root for path traversal issues."""

    def test_find_project_root_with_circular_symlinks(self):
        """Test find_project_root handles circular symlinks safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a circular symlink structure (if possible)
            dir1 = tmppath / "dir1"
            dir2 = tmppath / "dir2"
            dir1.mkdir()
            dir2.mkdir()

            try:
                (dir1 / "link_to_dir2").symlink_to(dir2)
                (dir2 / "link_to_dir1").symlink_to(dir1)
            except OSError:
                pytest.skip("Cannot create symlinks on this system")

            # Should not cause infinite loop
            result = find_project_root(str(dir1))

            # Should eventually return None or a valid path (may return string)
            assert result is None or isinstance(result, (Path, str))

    def test_find_project_root_stops_at_root(self):
        """Test find_project_root stops at filesystem root."""
        # Start from root directory
        result = find_project_root("/")

        # Should handle root directory gracefully (may return string)
        assert result is None or result == Path("/") or result == "/"
