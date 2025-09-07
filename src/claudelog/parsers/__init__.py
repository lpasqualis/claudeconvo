"""Parser system for handling different Claude log format versions."""

from .registry import get_parser, detect_version

__all__ = ['get_parser', 'detect_version']