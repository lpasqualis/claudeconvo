"""
claudeconvo - View Claude Code session history as a conversation.

A command-line utility to view and analyze Claude Code session files stored
in ~/.claude/projects/, formatted as readable conversations with colored output.
"""

__version__ = "0.2.0"
__author__  = "Lorenzo Pasqualis"

from .claudeconvo import main

__all__ = ["main"]
