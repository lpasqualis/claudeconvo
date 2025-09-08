"""
Allow claudeconvo to be run as a module with python -m claudeconvo.

This module serves as the entry point when the package is executed directly
using `python -m claudeconvo`. It imports and calls the main CLI function.
"""

from .cli import main

if __name__ == "__main__":
    main()
