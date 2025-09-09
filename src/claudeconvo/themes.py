"""Color theme definitions for claudeconvo.

This module provides a flexible color theming system using ANSI escape codes.
It supports multiple built-in themes and allows runtime theme switching.

Built-in themes:
  - dark: Optimized for dark terminal backgrounds (default)
  - light: Optimized for light terminal backgrounds
  - solarized-dark: Solarized Dark color scheme
  - solarized-light: Solarized Light color scheme
  - dracula: Dracula color theme
  - nord: Nord color theme
  - mono: Monochrome (no colors, only bold/dim)
  - high-contrast: High contrast colors for accessibility

The theme system uses:
  - Inheritance: Themes inherit from ColorTheme base class
  - Runtime switching: Colors proxy allows changing themes without restart
  - Semantic colors: Named by purpose (USER, ASSISTANT, ERROR) not hue
  - ANSI codes: Direct terminal escape sequences for maximum compatibility

Color categories:
  - Message types: USER, ASSISTANT, SYSTEM
  - Tool-related: TOOL_NAME, TOOL_PARAM, TOOL_OUTPUT
  - Status: ERROR, WARNING, SUCCESS
  - UI elements: SEPARATOR, METADATA, TIMESTAMP
  - Formatting: BOLD, DIM, RESET

The Colors object is a proxy that delegates to the current theme,
allowing themes to be changed at runtime via set_theme().
"""


################################################################################

class ColorTheme:
    """Base class for color themes."""

    name = "base"

    # Base attributes - all themes inherit or override these
    RESET = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"

    # Message types
    USER      = ""
    ASSISTANT = ""
    SYSTEM    = ""
    ERROR     = ""
    WARNING   = ""

    # Tool colors
    TOOL_NAME   = ""
    TOOL_PARAM  = ""
    TOOL_OUTPUT = ""

    # Other
    TIMESTAMP = ""
    SEPARATOR = ""
    METADATA  = ""


################################################################################

class DarkTheme(ColorTheme):
    """Default dark terminal theme."""

    name = "dark"

    # Message types
    USER      = "\033[36m"  # Cyan
    ASSISTANT = "\033[32m"  # Green
    SYSTEM    = "\033[33m"  # Yellow
    ERROR     = "\033[31m"  # Red
    WARNING   = "\033[33m"  # Yellow

    # Tool colors
    TOOL_NAME   = "\033[35m"  # Magenta
    TOOL_PARAM  = "\033[95m"  # Light magenta
    TOOL_OUTPUT = "\033[95m"  # Light magenta (same as tool params)

    # Other
    TIMESTAMP = "\033[37m"  # Light gray/white
    SEPARATOR = "\033[37m"  # White
    METADATA  = "\033[94m"  # Light blue


################################################################################

class LightTheme(ColorTheme):
    """Theme optimized for light/white terminals."""

    name = "light"

    # Message types - using bold for better readability on white
    USER      = "\033[1;34m"  # Bold blue
    ASSISTANT = "\033[1;30m"  # Bold black (very readable on white)
    SYSTEM    = "\033[35m"    # Magenta (readable on white)
    ERROR     = "\033[31m"    # Red
    WARNING   = "\033[33m"    # Yellow/Brown (kept for visibility)

    # Tool colors - high contrast on white background
    TOOL_NAME   = "\033[1;35m"  # Bold magenta (better contrast)
    TOOL_PARAM  = "\033[35m"   # Dark purple/magenta (good contrast)
    TOOL_OUTPUT = "\033[35m"   # Dark purple/magenta (consistent with params)

    # Other
    TIMESTAMP = "\033[90m"  # Dark gray
    SEPARATOR = "\033[94m"  # Blue (better than gray for summaries on white)
    METADATA = "\033[30m"   # Black (better than cyan on white)


################################################################################

class SolarizedDarkTheme(ColorTheme):
    """Solarized dark color scheme."""

    name = "solarized-dark"

    # Solarized base colors
    USER      = "\033[36m"  # Cyan
    ASSISTANT = "\033[32m"  # Green
    SYSTEM    = "\033[33m"  # Yellow
    ERROR     = "\033[31m"  # Red
    WARNING   = "\033[33m"  # Yellow

    # Tool colors
    TOOL_NAME   = "\033[35m"  # Magenta
    TOOL_PARAM  = "\033[34m"  # Blue
    TOOL_OUTPUT = "\033[90m"  # Base01

    # Other
    TIMESTAMP = "\033[37m"  # Base1
    SEPARATOR = "\033[37m"  # Base1
    METADATA  = "\033[36m"  # Cyan


################################################################################

class SolarizedLightTheme(ColorTheme):
    """Solarized light color scheme."""

    name = "solarized-light"

    # Solarized light adjustments
    USER      = "\033[36m"  # Cyan
    ASSISTANT = "\033[32m"  # Green
    SYSTEM    = "\033[35m"  # Magenta (better on light background)
    ERROR     = "\033[31m"  # Red
    WARNING   = "\033[33m"  # Yellow (kept for visibility)

    # Tool colors
    TOOL_NAME   = "\033[35m"  # Magenta
    TOOL_PARAM  = "\033[34m"  # Blue
    TOOL_OUTPUT = "\033[90m"  # Base00

    # Other
    TIMESTAMP = "\033[90m"  # Base00
    SEPARATOR = "\033[34m"  # Blue (better for summaries on light)
    METADATA  = "\033[36m"  # Cyan


################################################################################

class DraculaTheme(ColorTheme):
    """Dracula color scheme."""

    name = "dracula"

    # Dracula palette
    USER = "\033[36m"  # Cyan
    ASSISTANT = "\033[32m"  # Green
    SYSTEM = "\033[33m"  # Yellow
    ERROR = "\033[91m"  # Light red
    WARNING = "\033[93m"  # Bright yellow

    # Tool colors
    TOOL_NAME = "\033[95m"  # Light magenta
    TOOL_PARAM = "\033[35m"  # Magenta
    TOOL_OUTPUT = "\033[90m"  # Comment gray

    # Other
    TIMESTAMP = "\033[37m"  # Foreground
    SEPARATOR = "\033[35m"  # Purple
    METADATA = "\033[94m"  # Light blue


################################################################################

class NordTheme(ColorTheme):
    """Nord color scheme."""

    name = "nord"

    # Nord palette
    USER = "\033[96m"  # Nord8 - Bright cyan
    ASSISTANT = "\033[92m"  # Nord14 - Green
    SYSTEM = "\033[93m"  # Nord13 - Yellow
    ERROR = "\033[91m"  # Nord11 - Red
    WARNING = "\033[93m"  # Nord13 - Yellow

    # Tool colors
    TOOL_NAME = "\033[95m"  # Nord15 - Purple
    TOOL_PARAM = "\033[94m"  # Nord9 - Light blue
    TOOL_OUTPUT = "\033[90m"  # Nord3 - Gray

    # Other
    TIMESTAMP = "\033[37m"  # Nord4
    SEPARATOR = "\033[37m"  # Nord4
    METADATA = "\033[96m"  # Nord7


################################################################################

class MonoTheme(ColorTheme):
    """Monochrome theme with no colors."""

    name = "mono"

    # Override all with empty strings
    RESET = ""
    BOLD = ""
    DIM = ""


################################################################################

class HighContrastTheme(ColorTheme):
    """High contrast theme for accessibility."""

    name = "high-contrast"

    # Maximum contrast colors
    USER = "\033[1;36m"  # Bold cyan
    ASSISTANT = "\033[1;32m"  # Bold green
    SYSTEM = "\033[1;33m"  # Bold yellow
    ERROR = "\033[1;31m"  # Bold red
    WARNING = "\033[1;33m"  # Bold yellow

    # Tool colors
    TOOL_NAME = "\033[1;35m"  # Bold magenta
    TOOL_PARAM = "\033[1;34m"  # Bold blue
    TOOL_OUTPUT = "\033[0m"  # Normal

    # Other
    TIMESTAMP = "\033[1;37m"  # Bold white
    SEPARATOR = "\033[1;37m"  # Bold white
    METADATA = "\033[1;36m"  # Bold cyan


# Theme registry
THEMES = {
    "dark": DarkTheme,
    "light": LightTheme,
    "solarized-dark": SolarizedDarkTheme,
    "solarized-light": SolarizedLightTheme,
    "dracula": DraculaTheme,
    "nord": NordTheme,
    "mono": MonoTheme,
    "high-contrast": HighContrastTheme,
}

# Theme descriptions for help text
THEME_DESCRIPTIONS = {
    "dark": "Optimized for dark terminals (default)",
    "light": "Optimized for light/white terminals",
    "solarized-dark": "Solarized dark color scheme",
    "solarized-light": "Solarized light color scheme",
    "dracula": "Dracula color scheme",
    "nord": "Nord color scheme",
    "mono": "No colors (monochrome)",
    "high-contrast": "Maximum contrast for accessibility",
}


def get_color_theme(theme_name: str = "dark") -> ColorTheme:
    """Get a color theme instance by name.

    Args:
        theme_name: Name of the theme (default: 'dark')

    Returns:
        ColorTheme instance
    """
    theme_class = THEMES.get(theme_name, DarkTheme)
    return theme_class()


# Global Colors instance - will be updated based on theme selection
# Using a wrapper class to allow runtime theme changes
################################################################################

class _ColorsWrapper:
    """Wrapper to allow dynamic theme switching."""

    ################################################################################

    def __init__(self) -> None:
        self._theme = DarkTheme()

    ################################################################################

    def set_theme(self, theme: ColorTheme) -> None:
        """Set the current theme."""
        self._theme = theme  # type: ignore[assignment]

    ################################################################################

    def __getattr__(self, name: str) -> str:
        """Delegate attribute access to the current theme."""
        return getattr(self._theme, name)  # type: ignore[no-any-return]


# Single global instance that can be updated
Colors = _ColorsWrapper()
