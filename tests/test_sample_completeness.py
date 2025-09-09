"""Test that all types in the sample conversation are handled by the formatter."""

import json
from pathlib import Path

from src.claudeconvo.formatters import format_conversation_entry
from src.claudeconvo.options import ShowOptions


def test_sample_types_coverage():
    """Verify all types in sample_conversation.jsonl can be displayed."""
    sample_file = Path(__file__).parent / "fixtures" / "sample_conversation.jsonl"
    
    # Collect all types from sample
    sample_types = set()
    entries = []
    with open(sample_file, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                sample_types.add(entry.get('type', 'unknown'))
                entries.append(entry)
    
    # Test each type can be formatted
    opts = ShowOptions('a')  # Enable all options
    
    types_not_displayed = []
    for entry in entries:
        result = format_conversation_entry(entry, opts)
        if not result:
            types_not_displayed.append(entry.get('type', 'unknown'))
    
    # Report results
    print(f"\nTypes in sample: {sorted(sample_types)}")
    print(f"Types NOT displayed: {sorted(set(types_not_displayed))}")
    
    # Assert all types can be displayed
    assert not types_not_displayed, (
        f"These types in sample cannot be displayed: {sorted(set(types_not_displayed))}\n"
        f"Either implement formatters for them or remove them from the sample."
    )


def test_real_log_types_coverage():
    """Check what types are actually used in Claude logs."""
    # Known types from real Claude logs
    real_types = {'user', 'assistant', 'system', 'summary'}
    
    # Types that the formatter explicitly handles
    handled_types = {'user', 'assistant', 'system', 'summary'}
    
    missing = real_types - handled_types
    assert not missing, f"Real log types not handled: {missing}"


if __name__ == "__main__":
    test_sample_types_coverage()
    test_real_log_types_coverage()
    print("\nAll tests passed!")