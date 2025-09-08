"""
Parser system for handling different Claude log format versions.

This package provides an adaptive parser system that can handle various
Claude Code log format versions automatically, ensuring compatibility
as the format evolves over time.
"""

from .registry import get_parser

__all__ = ["get_parser"]
