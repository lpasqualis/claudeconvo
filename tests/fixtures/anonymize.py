#!/usr/bin/env python3
"""Anonymize fixture data to remove sensitive information."""

import json
import re
from pathlib import Path
import hashlib
import random

# Anonymization patterns
PATTERNS = {
    # File paths
    r'/Users/[^/\s"]+': "/Users/anonymous",
    r'/home/[^/\s"]+': "/home/user",
    r"C:\\\\Users\\\\[^\\\\]+": r"C:\\Users\\User",
    # Common directories
    r'/Dropbox[^/\s"]*': "/Projects",
    r'/Google Drive[^/\s"]*': "/Documents",
    r'/OneDrive[^/\s"]*': "/Files",
    r'/iCloud[^/\s"]*': "/Cloud",
    # Project names (preserve structure but anonymize)
    r"WritingWithClaude": "ExampleProject",
    r"claudelog": "LogViewer",
    r"acor-cli": "CLI-Tool",
    r"lpclaude": "DevProject",
    # Git branches (skip main/master/develop)
    r'"gitBranch":\s*"(?!main|master|develop)[^"]+"': '"gitBranch": "feature-branch"',
    # UUIDs - replace with deterministic fake UUIDs
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}": "UUID_PLACEHOLDER",
    # Session IDs
    r'"sessionId":\s*"[^"]+"': '"sessionId": "session-xxx"',
    r'"requestId":\s*"[^"]+"': '"requestId": "req-xxx"',
    r'"parentUuid":\s*"[^"]+"': '"parentUuid": "parent-xxx"',
    r'"leafUuid":\s*"[^"]+"': '"leafUuid": "leaf-xxx"',
    r'"toolUseID":\s*"[^"]+"': '"toolUseID": "tool-xxx"',
    # Tool IDs
    r'"id":\s*"toolu_[^"]+"': '"id": "toolu_xxx"',
    r'"id":\s*"msg_[^"]+"': '"id": "msg_xxx"',
    # File paths in content
    r'"/[^"]*\.(py|js|ts|md|txt|json)"': '"/path/to/file.ext"',
    # Email addresses
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}": "user@example.com",
    # IP addresses
    r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b": "192.168.1.1",
    # Timestamps (keep format but use fixed dates)
    r'"timestamp":\s*"20\d{2}-\d{2}-\d{2}T[^"]+"': '"timestamp": "2025-01-01T12:00:00.000Z"',
}

# Sample generic content for different message types
GENERIC_CONTENT = {
    "user": [
        "Can you help me with this code?",
        "Please explain this function",
        "How do I implement this feature?",
        "What's the best approach for this?",
        "Can you review this implementation?",
    ],
    "assistant": [
        "I'll help you with that implementation.",
        "Let me analyze the code for you.",
        "Here's how you can approach this:",
        "I've reviewed the code and found the following:",
        "Let me explain how this works:",
    ],
    "system": [
        "Command executed successfully",
        "Process completed",
        "Hook executed",
        "Session started",
        "Configuration loaded",
    ],
    "summary": [
        "Code review and implementation",
        "Bug fix and testing",
        "Feature development",
        "Documentation update",
        "Refactoring session",
    ],
}


def generate_fake_uuid(seed_string):
    """Generate a deterministic fake UUID based on input."""
    hash_obj = hashlib.md5(seed_string.encode())
    hex_str = hash_obj.hexdigest()
    return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"


def anonymize_content(content, entry_type="user"):
    """Anonymize message content."""
    if isinstance(content, str):
        # First check if it contains sensitive info that needs complete replacement
        if any(
            pattern in content.lower()
            for pattern in ["lpasqualis", "lorenzo", "pasqualis", "dreambox", "uievolution"]
        ):
            return random.choice(GENERIC_CONTENT.get(entry_type, GENERIC_CONTENT["user"]))
        # Replace with generic content
        if len(content) > 100:  # Long content
            return random.choice(GENERIC_CONTENT.get(entry_type, GENERIC_CONTENT["user"]))
        elif content.strip():  # Short content
            return "Sample text"
        return content  # Empty or whitespace

    elif isinstance(content, list):
        anonymized = []
        for item in content:
            if isinstance(item, dict):
                item_copy = item.copy()

                # Anonymize text content
                if "text" in item_copy:
                    item_copy["text"] = anonymize_content(item_copy["text"], entry_type)
                if "content" in item_copy:
                    item_copy["content"] = anonymize_content(item_copy["content"], entry_type)

                # Anonymize tool inputs
                if "input" in item_copy and isinstance(item_copy["input"], dict):
                    for key in item_copy["input"]:
                        if key in ["file_path", "path", "filepath"]:
                            item_copy["input"][key] = "/path/to/file"
                        elif key in ["command", "cmd"]:
                            item_copy["input"][key] = 'echo "test command"'
                        elif key in ["content", "text", "code"]:
                            item_copy["input"][key] = "sample content"
                        else:
                            item_copy["input"][key] = "value"

                # Anonymize tool names
                if "name" in item_copy:
                    if item_copy["name"] in ["Read", "Write", "Edit", "Bash"]:
                        pass  # Keep tool names
                    else:
                        item_copy["name"] = "CustomTool"

                anonymized.append(item_copy)
            else:
                anonymized.append(item)
        return anonymized

    return content


def anonymize_entry(entry):
    """Anonymize a single log entry."""
    # Convert to JSON string for pattern replacement
    entry_str = json.dumps(entry, ensure_ascii=False)

    # Apply all patterns
    for pattern, replacement in PATTERNS.items():
        if "UUID_PLACEHOLDER" in replacement:
            # Special handling for UUIDs
            matches = re.findall(pattern, entry_str)
            for match in matches:
                fake_uuid = generate_fake_uuid(match)
                entry_str = entry_str.replace(match, fake_uuid)
        else:
            entry_str = re.sub(pattern, replacement, entry_str)

    # Parse back to dict
    anonymized = json.loads(entry_str)

    # Anonymize message content
    if "message" in anonymized and isinstance(anonymized["message"], dict):
        if "content" in anonymized["message"]:
            entry_type = anonymized.get("type", "user")
            anonymized["message"]["content"] = anonymize_content(
                anonymized["message"]["content"], entry_type
            )

    # Anonymize summary content
    if "summary" in anonymized and isinstance(anonymized["summary"], str):
        anonymized["summary"] = random.choice(GENERIC_CONTENT["summary"])

    # Anonymize system content
    if "content" in anonymized and anonymized.get("type") == "system":
        anonymized["content"] = random.choice(GENERIC_CONTENT["system"])

    # Anonymize tool results
    if "toolUseResult" in anonymized:
        if isinstance(anonymized["toolUseResult"], str):
            anonymized["toolUseResult"] = "Tool execution successful"
        elif isinstance(anonymized["toolUseResult"], list):
            anonymized["toolUseResult"] = ["Result 1", "Result 2"]

    return anonymized


def anonymize_fixtures():
    """Anonymize all fixture files."""
    fixtures_dir = Path("tests/fixtures/versions")

    if not fixtures_dir.exists():
        print("No fixtures directory found")
        return

    for version_file in fixtures_dir.glob("*.json"):
        if version_file.name == "summary.json":
            continue  # Skip summary file

        print(f"Anonymizing {version_file.name}...")

        with open(version_file) as f:
            data = json.load(f)

        # Anonymize each entry
        for entry_type, entries in data["entry_types"].items():
            anonymized_entries = []
            for entry in entries:
                anonymized_entries.append(anonymize_entry(entry))
            data["entry_types"][entry_type] = anonymized_entries

        # Save anonymized version
        with open(version_file, "w") as f:
            json.dump(data, f, indent=2)

    print("Anonymization complete!")


def verify_anonymization():
    """Verify no sensitive data remains."""
    fixtures_dir = Path("tests/fixtures/versions")

    sensitive_patterns = [
        r"lpasqualis",
        r'/Users/(?!anonymous)[^/\s"]+',  # Any username except 'anonymous'
        r"Dropbox",
        r"Google Drive",
        r"OneDrive",
        r"@anthropic",
        r"@gmail",
        r"WritingWithClaude",  # Original project names (now should be ExampleProject)
    ]

    issues = []

    for version_file in fixtures_dir.glob("*.json"):
        if version_file.name == "summary.json":
            continue

        with open(version_file) as f:
            content = f.read()

        for pattern in sensitive_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(f"{version_file.name}: Found '{matches[0]}' (pattern: {pattern})")

    if issues:
        print("⚠️  Sensitive data found:")
        for issue in issues[:10]:
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        return False
    else:
        print("✅ No sensitive data found in fixtures")
        return True


if __name__ == "__main__":
    print("Anonymizing fixture data...")
    anonymize_fixtures()
    print("\nVerifying anonymization...")
    verify_anonymization()
