"""Constants for integration_blueprint."""
# Base component constants
NAME = "Deako"
DOMAIN = "deako"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
ISSUE_URL = "https://github.com/custom-components/integration_blueprint/issues"

# Icons
ICON = "mdi:format-quote-close"

# Platforms
LIGHT = "light"
PLATFORMS = [LIGHT]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_IP = "ip"

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
