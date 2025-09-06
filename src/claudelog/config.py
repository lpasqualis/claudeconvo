"""Configuration management for claudelog."""

import json
import os
from pathlib import Path


def load_config():
    """Load configuration from ~/.claudelogrc if it exists.

    Returns:
        dict: Configuration values or empty dict if no config file
    """
    config_path = Path.home() / '.claudelogrc'
    if not config_path.exists():
        return {}

    try:
        with open(config_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        # Silently ignore config errors and use defaults
        return {}


def determine_theme(args, config=None):
    """Determine which theme to use based on priority order.

    Priority:
    1. Command-line argument (--theme or --no-color)
    2. Environment variable (CLAUDELOG_THEME)
    3. Config file (~/.claudelogrc)
    4. Default ('dark')

    Args:
        args: Parsed command-line arguments
        config: Configuration dict from file (optional)

    Returns:
        str: Theme name
    """
    # 1. Command-line has highest priority
    if hasattr(args, 'theme') and args.theme and args.theme != 'list':
        return args.theme
    if hasattr(args, 'no_color') and args.no_color:
        return 'mono'

    # 2. Environment variable
    env_theme = os.environ.get('CLAUDELOG_THEME')
    if env_theme:
        return env_theme

    # 3. Config file
    if config and 'theme' in config:
        return config['theme']

    # 4. Default
    return 'dark'
