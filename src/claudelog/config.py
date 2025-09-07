"""Configuration management for claudelog."""

import os
from pathlib import Path

from .utils import load_json_config


def load_config():
    """Load configuration from config file.

    Looks for config in this order:
    1. CLAUDELOG_CONFIG environment variable
    2. XDG_CONFIG_HOME/claudelog/config.json (if XDG_CONFIG_HOME is set)
    3. ~/.config/claudelog/config.json
    4. ~/.claudelogrc (legacy location)

    Returns:
        dict: Configuration values or empty dict if no config file
    """
    # Check environment variable first
    env_config = os.environ.get("CLAUDELOG_CONFIG")
    if env_config:
        config_path = Path(env_config)
        if config_path.exists():
            return load_json_config(config_path, default={})

    # Check XDG config directory
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_path = Path(xdg_config) / "claudelog" / "config.json"
        if config_path.exists():
            return load_json_config(config_path, default={})

    # Check ~/.config/claudelog/config.json
    config_path = Path.home() / ".config" / "claudelog" / "config.json"
    if config_path.exists():
        return load_json_config(config_path, default={})

    # Check legacy location
    config_path = Path.home() / ".claudelogrc"
    return load_json_config(config_path, default={})


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
    if hasattr(args, "theme") and args.theme and args.theme != "list":
        return args.theme
    if hasattr(args, "no_color") and args.no_color:
        return "mono"

    # 2. Environment variable
    env_theme = os.environ.get("CLAUDELOG_THEME")
    if env_theme:
        return env_theme

    # 3. Config file
    if config and "theme" in config:
        return config["theme"]

    # 4. Default
    return "dark"
