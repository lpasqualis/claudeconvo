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
from typing import Any

from .constants import CONFIG_FILE_PATH
from .utils import load_json_config

################################################################################


def _normalize_config_keys(config: dict) -> dict:
    """
    Normalize config keys for backwards compatibility.

    Handles both old format (theme, style, show_options, watch) and
    new format (default_theme, default_style, default_show_options, default_watch).

    Args:
        config: Raw configuration dict

    Returns:
        dict: Normalized configuration with default_ prefixed keys
    """
    normalized = {}

    # Map old keys to new keys
    key_mapping = {
        "theme": "default_theme",
        "style": "default_style",
        "show_options": "default_show_options",
        "watch": "default_watch"
    }

    for old_key, new_key in key_mapping.items():
        # Check for both old and new format
        if old_key in config:
            normalized[new_key] = config[old_key]
        elif new_key in config:
            normalized[new_key] = config[new_key]

    # Preserve any other keys that might exist
    for key, value in config.items():
        if key not in key_mapping and key not in normalized:
            normalized[key] = value

    return normalized


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
            config = load_json_config(config_path, default={})
            return _normalize_config_keys(config)

    # Check XDG config directory
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        config_path = Path(xdg_config) / "claudeconvo" / "config.json"
        if config_path.exists():
            config = load_json_config(config_path, default={})
            return _normalize_config_keys(config)

    # Check ~/.config/claudeconvo/config.json
    config_path = Path.home() / ".config" / "claudeconvo" / "config.json"
    if config_path.exists():
        config = load_json_config(config_path, default={})
        return _normalize_config_keys(config)

    # Check legacy location
    config_path = Path(CONFIG_FILE_PATH)
    config = load_json_config(config_path, default={})
    return _normalize_config_keys(config)


################################################################################

def determine_theme(
    args   : Any,
    config : dict | None = None
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

    # 3. Config file (now uses normalized key)
    if config and "default_theme" in config:
        return str(config["default_theme"])

    # 4. Default
    return "dark"
