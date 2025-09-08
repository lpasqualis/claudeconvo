"""
View Claude Code session history as a conversation.

This utility loads and displays session files stored in ~/.claude/projects/
for the current working directory, formatted as a readable conversation with
colored output for different speakers and tool executions.
"""

# Import main from cli for backward compatibility
from .cli import main

__all__ = ["main"]
