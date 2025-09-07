"""Constants for claudelog."""

import os

# File size limits
BYTES_PER_KB = 1024
BYTES_PER_MB = BYTES_PER_KB * 1024
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * BYTES_PER_MB

# Display formatting
UUID_DISPLAY_LENGTH = 8
FILENAME_DISPLAY_WIDTH = 44
SEPARATOR_WIDTH = 70
LIST_ITEM_NUMBER_WIDTH = 3

# Parser limits
MAX_RECURSION_DEPTH = 20

# Truncation limits (these can be overridden by ShowOptions)
DEFAULT_TRUNCATION_LIMITS = {
    "tool_param": 200,
    "tool_result": 500,
    "default": 500,
    "error": 1000,
    "error_short": 500,
}

# Display limits for diagnostics
MAX_PARSE_ERRORS_DISPLAY = 10
MAX_FIELD_PATTERNS_DISPLAY = 20
MAX_TYPE_COUNTS_DISPLAY = 20

# Default paths
# Allow overriding the Claude projects directory via environment variable
CLAUDE_PROJECTS_DIR = os.environ.get("CLAUDE_PROJECTS_DIR", ".claude/projects")
