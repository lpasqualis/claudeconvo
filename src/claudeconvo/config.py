"""
Configuration management for claudeconvo.

This module handles loading configuration from various sources including
environment variables, XDG config directories, and legacy locations.
It also manages theme selection based on priority order.

Example usage:
    config = load_config()
    theme = determine_theme(args, config)
"""

import os
from pathlib import Path
from typing import Any, Optional

from .utils import load_json_config

################################################################################


def load_config() -> dict:
    """
    Load configuration from config file.

    Looks for config in this order:
    1. CLAUDECONVO_CONFIG environment variable
    2. XDG_CONFIG_HOME/claudeconvo/config.json (if XDG_CONFIG_HOME is set)
    3. ~/.config/claudeconvo/config.json
    4. ~/.claudeconvorc (legacy location)

    Returns:
        dict: Configuration values or empty dict if no config file
    """
    # Check environment variable first
    env_config = os.environ.get("CLAUDECONVO_CONFIG")
    if env_config:
        config_path = Path(env_config)
        if config_path.exists():
            return load_json_config(config_path, default={})

    # Check XDG config directory
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_path = Path(xdg_config) / "claudeconvo" / "config.json"
        if config_path.exists():
            return load_json_config(config_path, default={})

    # Check ~/.config/claudeconvo/config.json
    config_path = Path.home() / ".config" / "claudeconvo" / "config.json"
    if config_path.exists():
        return load_json_config(config_path, default={})

    # Check legacy location
    config_path = Path.home() / ".claudeconvorc"
    return load_json_config(config_path, default={})


################################################################################

def determine_theme(
    args   : Any,
    config : Optional[dict] = None
) -> str:
    """
    Determine which theme to use based on priority order.

    Priority:
    1. Command-line argument (--theme or --no-color)
    2. Environment variable (CLAUDECONVO_THEME)
    3. Config file (~/.claudeconvorc)
    4. Default ('dark')

    Args:
        args: Parsed command-line arguments
        config: Configuration dict from file (optional)

    Returns:
        str: Theme name
    """
    # 1. Command-line has highest priority
    if hasattr(args, "theme") and args.theme and args.theme != "list":
        return str(args.theme)
    if hasattr(args, "no_color") and args.no_color:
        return "mono"

    # 2. Environment variable
    env_theme = os.environ.get("CLAUDECONVO_THEME")
    if env_theme:
        return str(env_theme)

    # 3. Config file
    if config and "theme" in config:
        return str(config["theme"])

    # 4. Default
    return "dark"
