"""Tests for the adaptive parser."""

import json
import pytest
from src.claudelog.parsers.adaptive import AdaptiveParser


class TestAdaptiveParser:
    """Test the adaptive parser with various log formats."""
    
    def test_parse_v1_0_70_format(self):
        """Test parsing v1.0.70 format."""
        entry = {
            "type": "user",
            "version": "1.0.70",
            "timestamp": "2025-08-07T22:44:29.353Z",
            "sessionId": "test-session",
            "message": {
                "role": "user",
                "content": "Hello, Claude"
            }
        }
        
        parser = AdaptiveParser()
        result = parser.parse_entry(entry)
        
        assert result['type'] == 'user'
        assert result['version'] == '1.0.70'
        assert result['message']['role'] == 'user'
        assert result['message']['content'] == 'Hello, Claude'
    
    def test_parse_v1_0_85_format(self):
        """Test parsing v1.0.85 format with tool use."""
        entry = {
            "type": "assistant",
            "version": "1.0.85",
            "timestamp": "2025-08-20T22:00:25.956Z",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Let me help you with that."
                    },
                    {
                        "type": "tool_use",
                        "id": "tool_123",
                        "name": "Read",
                        "input": {"file_path": "/test/file.txt"}
                    }
                ]
            }
        }
        
        parser = AdaptiveParser()
        result = parser.parse_entry(entry)
        
        assert result['type'] == 'assistant'
        assert result['version'] == '1.0.85'
        assert result['message']['role'] == 'assistant'
        
        # Extract text
        text = parser.extract_content_text(result)
        assert "Let me help you with that." in text
        
        # Extract tool info
        tool_info = parser.extract_tool_info(result)
        assert len(tool_info['tool_uses']) == 1
        assert tool_info['tool_uses'][0]['name'] == 'Read'
    
    def test_parse_summary_entry(self):
        """Test parsing summary entries."""
        entry = {
            "type": "summary",
            "summary": "Test session summary",
            "leafUuid": "uuid-123"
        }
        
        parser = AdaptiveParser()
        result = parser.parse_entry(entry)
        
        assert result['type'] == 'summary'
        assert result['summary'] == 'Test session summary'
        assert result['leafUuid'] == 'uuid-123'
    
    def test_parse_unknown_format(self):
        """Test parsing future/unknown format gracefully."""
        entry = {
            "kind": "message",  # Different field name
            "ver": "2.0.0",  # Different version field
            "created": "2025-12-01T00:00:00Z",  # Different timestamp field
            "data": {  # Different message field
                "sender": "human",  # Different role field
                "text": "Future format test"  # Different content field
            },
            "new_field": "unknown_value"  # Unknown field
        }
        
        parser = AdaptiveParser()
        result = parser.parse_entry(entry)
        
        # Should still extract what it can
        assert result['type'] == 'message'  # From 'kind'
        assert result['version'] == '2.0.0'  # From 'ver'
        assert result['timestamp'] == '2025-12-01T00:00:00Z'  # From 'created'
        assert '_unknown_new_field' in result  # Unknown fields preserved
        
        # Message should be extracted
        assert result['message'] is not None
        assert result['message']['role'] == 'human'  # From 'sender'
    
    def test_extract_complex_content(self):
        """Test extracting text from complex nested content."""
        parser = AdaptiveParser()
        
        # Test various content formats
        test_cases = [
            # Simple string
            ("Hello", "Hello"),
            
            # Array of text objects
            ([{"type": "text", "text": "Part 1"}, {"type": "text", "text": "Part 2"}], 
             "Part 1\nPart 2"),
            
            # Nested content
            ({"content": {"text": "Nested text"}}, "Nested text"),
            
            # Mixed array
            ([{"text": "Text 1"}, "String directly", {"content": "Text 2"}],
             "Text 1\nString directly\nText 2"),
        ]
        
        for content, expected in test_cases:
            result = parser._extract_text_from_content(content)
            assert result == expected
    
    def test_field_discovery(self):
        """Test field discovery with aliases."""
        parser = AdaptiveParser()
        
        # Test finding fields with various aliases
        obj = {
            "timestamp": "2025-01-01",
            "cwd": "/home/user",
            "gitBranch": "main"
        }
        
        assert parser._find_field(obj, ['timestamp', 'time', 'created']) == '2025-01-01'
        assert parser._find_field(obj, ['cwd', 'pwd', 'path']) == '/home/user'
        assert parser._find_field(obj, ['gitBranch', 'branch']) == 'main'
        assert parser._find_field(obj, ['missing', 'nothere']) is None
    
    def test_tool_result_extraction(self):
        """Test extracting tool results."""
        entry = {
            "type": "user",
            "toolUseResult": "File read successfully"
        }
        
        parser = AdaptiveParser()
        result = parser.parse_entry(entry)
        
        assert result['toolUseResult'] == "File read successfully"
        
        # Test with alternative field name
        entry2 = {
            "type": "user",
            "tool_result": "Command executed"
        }
        
        result2 = parser.parse_entry(entry2)
        # Should find it through field aliases
        assert result2['toolUseResult'] == "Command executed" or \
               result2.get('_unknown_tool_result') == "Command executed"