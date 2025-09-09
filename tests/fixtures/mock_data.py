"""Mock data for testing and demonstration purposes."""

import json
from pathlib import Path
from typing import Any, Dict, List


def get_sample_messages() -> List[Dict[str, Any]]:
    """Get sample messages demonstrating ALL message types.
    
    First tries to load from sample_conversation.jsonl, then falls back
    to minimal hardcoded data if needed.
    """
    # Try to load from JSONL file first
    sample_file = Path(__file__).parent / "sample_conversation.jsonl"
    
    if sample_file.exists():
        messages = []
        try:
            with open(sample_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        messages.append(json.loads(line))
            if messages:
                return messages
        except (json.JSONDecodeError, IOError):
            # Fall back to hardcoded data if file is corrupted
            pass
    
    # Fallback: Return minimal hardcoded sample if file not found or corrupted
    return get_minimal_sample_messages()


def get_minimal_sample_messages() -> List[Dict[str, Any]]:
    """Get minimal hardcoded sample messages for testing."""
    return [
        {
            "type": "user",
            "message": {"content": "Hello, can you help me with a Python question?"},
            "timestamp": "2024-01-15T10:30:00Z"
        },
        {
            "type": "assistant",
            "message": {"content": "Of course! I'd be happy to help you with your Python question. What would you like to know?"},
            "timestamp": "2024-01-15T10:30:05Z"
        }
    ]


def get_demo_session_data() -> Dict[str, Any]:
    """Get demo session data for interactive setup."""
    return {
        "sessions": [
            {
                "name": "Project Alpha",
                "timestamp": "2024-01-15T14:30:00Z",
                "id": "abc123",
                "last_message": "Working on refactoring the authentication module..."
            },
            {
                "name": "Bug Fix #342",
                "timestamp": "2024-01-15T09:15:00Z",
                "id": "def456",
                "last_message": "Fixed the memory leak in the data processor..."
            },
            {
                "name": "Feature: Dark Mode",
                "timestamp": "2024-01-14T16:45:00Z",
                "id": "ghi789",
                "last_message": "Implemented theme switching functionality..."
            }
        ]
    }