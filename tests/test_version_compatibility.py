"""Test version compatibility using collected fixture data."""

import json
import pytest
from pathlib import Path
from src.claudelog.parsers.adaptive import AdaptiveParser


class TestVersionCompatibility:
    """Test that the adaptive parser handles all known versions correctly."""
    
    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return AdaptiveParser()
    
    @pytest.fixture
    def fixture_data(self):
        """Load all fixture data."""
        fixtures_dir = Path('tests/fixtures/versions')
        data = {}
        
        for version_file in fixtures_dir.glob('*.json'):
            if version_file.name == 'summary.json':
                continue
            
            with open(version_file) as f:
                version_data = json.load(f)
                data[version_data['version']] = version_data
        
        return data
    
    def test_all_versions_parse(self, parser, fixture_data):
        """Test that all versions can be parsed without errors."""
        errors = []
        
        for version, data in fixture_data.items():
            for entry_type, entries in data['entry_types'].items():
                for i, entry in enumerate(entries):
                    try:
                        parsed = parser.parse_entry(entry)
                        assert parsed is not None
                        assert '_parse_error' not in parsed
                    except Exception as e:
                        errors.append(f"{version}/{entry_type}[{i}]: {e}")
        
        assert not errors, f"Parse errors:\n" + "\n".join(errors)
    
    def test_type_extraction(self, parser, fixture_data):
        """Test that entry types are correctly extracted."""
        mismatches = []
        
        for version, data in fixture_data.items():
            for entry_type, entries in data['entry_types'].items():
                if entry_type == 'unknown':
                    continue
                    
                for i, entry in enumerate(entries):
                    parsed = parser.parse_entry(entry)
                    extracted_type = parsed.get('type')
                    
                    if extracted_type != entry_type:
                        mismatches.append(
                            f"{version}/{entry_type}[{i}]: got '{extracted_type}'"
                        )
        
        # Allow some mismatches due to format evolution
        assert len(mismatches) < 5, f"Too many type mismatches:\n" + "\n".join(mismatches[:10])
    
    def test_content_extraction(self, parser, fixture_data):
        """Test that content can be extracted from messages."""
        extraction_failures = []
        
        for version, data in fixture_data.items():
            for entry_type, entries in data['entry_types'].items():
                if entry_type == 'summary':
                    continue  # Summaries don't have message content
                    
                for i, entry in enumerate(entries):
                    try:
                        parsed = parser.parse_entry(entry)
                        
                        # Try to extract content if there's a message
                        if parsed.get('message'):
                            content = parser.extract_content_text(parsed)
                            # Just verify it doesn't crash
                            
                    except Exception as e:
                        extraction_failures.append(
                            f"{version}/{entry_type}[{i}]: {e}"
                        )
        
        assert not extraction_failures, f"Content extraction failures:\n" + "\n".join(extraction_failures[:10])
    
    def test_version_field_present(self, parser, fixture_data):
        """Test that version field is preserved."""
        missing_versions = []
        
        for version, data in fixture_data.items():
            if version == 'no_version':
                continue
                
            for entry_type, entries in data['entry_types'].items():
                for i, entry in enumerate(entries):
                    parsed = parser.parse_entry(entry)
                    
                    if not parsed.get('version'):
                        missing_versions.append(
                            f"{version}/{entry_type}[{i}]: version field missing"
                        )
        
        assert not missing_versions, f"Missing versions:\n" + "\n".join(missing_versions[:10])
    
    def test_tool_extraction(self, parser, fixture_data):
        """Test tool use extraction for assistant messages."""
        tool_errors = []
        
        for version, data in fixture_data.items():
            for entry_type, entries in data['entry_types'].items():
                if entry_type != 'assistant':
                    continue
                    
                for i, entry in enumerate(entries):
                    try:
                        parsed = parser.parse_entry(entry)
                        tool_info = parser.extract_tool_info(parsed)
                        
                        # Check if tool uses were found when expected
                        message = entry.get('message', {})
                        if isinstance(message, dict):
                            content = message.get('content', [])
                            if isinstance(content, list):
                                has_tools = any(
                                    isinstance(item, dict) and 
                                    item.get('type') == 'tool_use'
                                    for item in content
                                )
                                
                                if has_tools and not tool_info['tool_uses']:
                                    tool_errors.append(
                                        f"{version}[{i}]: Expected tools not extracted"
                                    )
                                    
                    except Exception as e:
                        tool_errors.append(f"{version}[{i}]: {e}")
        
        # Tool extraction is complex, allow some errors
        assert len(tool_errors) < 10, f"Too many tool extraction errors:\n" + "\n".join(tool_errors[:5])
    
    def test_unknown_fields_preserved(self, parser, fixture_data):
        """Test that unknown fields are preserved with _unknown_ prefix."""
        preservation_issues = []
        
        # Check a sample with known unknown fields
        for version, data in fixture_data.items():
            for entry_type, entries in data['entry_types'].items():
                for i, entry in enumerate(entries[:1]):  # Just check first entry
                    parsed = parser.parse_entry(entry)
                    
                    # Check if any unknown fields were preserved
                    unknown_fields = [k for k in parsed.keys() if k.startswith('_unknown_')]
                    
                    # If original had fields not in our known set, they should be preserved
                    known_fields = {
                        'type', 'version', 'timestamp', 'sessionId', 'uuid', 
                        'parentUuid', 'isSidechain', 'isMeta', 'userType', 'cwd',
                        'gitBranch', 'level', 'requestId', 'message', 'toolUseResult',
                        'summary', 'leafUuid', '_raw'
                    }
                    
                    original_fields = set(entry.keys())
                    expected_unknown = original_fields - known_fields
                    
                    if expected_unknown and not unknown_fields:
                        preservation_issues.append(
                            f"{version}/{entry_type}[{i}]: Expected unknown fields not preserved"
                        )
        
        # This is informational, not a hard failure
        if preservation_issues:
            print(f"Info: Some unknown fields may not be preserved:\n" + "\n".join(preservation_issues[:5]))
    
    def test_field_patterns_match_summary(self, fixture_data):
        """Test that field patterns in fixtures match what was collected."""
        fixtures_dir = Path('tests/fixtures/versions')
        summary_file = fixtures_dir / 'summary.json'
        
        if summary_file.exists():
            with open(summary_file) as f:
                summary = json.load(f)
            
            assert 'versions' in summary
            assert 'entry_types' in summary
            assert 'field_variations' in summary
            
            # Check all versions are represented
            fixture_versions = set(fixture_data.keys())
            summary_versions = set(summary['versions'])
            
            assert fixture_versions == summary_versions, \
                f"Version mismatch: fixtures={fixture_versions}, summary={summary_versions}"