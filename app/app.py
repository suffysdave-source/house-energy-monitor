# File: app.py
# Description: Main Dash application for the House Energy Monitor, with dynamic page loading and Bootstrap styling.
# Version: 1.11
# Author: Dave (optimized with Grok)
# Created: 2025-10-19
# Last Modified: 2025-10-21

import os
import sys
from dash import Dash, html, page_container
import dash_bootstrap_components as dbc
import logging

# Suppress Dash and Flask logging
logging.getLogger("dash").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# Add project root to sys.path to resolve utils and scripts imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.logger import setup_logging
from utils.config import load_config

CONFIG = load_config()
logger = setup_logging(CONFIG.get("logging", {}))

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

navbar = html.Nav(
    className="navbar navbar-expand-lg navbar-light bg-light",
    children=[
        html.A("House Energy Monitor", className="navbar-brand", href="/"),
        html.Button(
            className="navbar-toggler",
            type="button",
            **{
                "data-bs-toggle": "collapse",
                "data-bs-target": "#navbarNav",
                "aria-controls": "navbarNav",
                "aria-expanded": "false",
                "aria-label": "Toggle navigation"
            },
            children=[html.Span(className="navbar-toggler-icon")]
        ),
        html.Div(
            className="collapse navbar-collapse",
            id="navbarNav",
            children=[
                html.Ul(
                    className="navbar-nav",
                    children=[
                        html.Li(
                            className="nav-item",
                            children=[
                                html.A(
                                    page["name"],
                                    className="nav-link",
                                    href=page["path"]
                                )
                            ]
                        )
                        for page in CONFIG.get("pages", {}).values()
                        if page.get("visible", False)
                    ]
                )
            ]
        )
    ]
)

app.layout = html.Div([
    navbar,
    page_container
])

if __name__ == "__main__":
    logger.info("Starting Dash application", extra={"device_id": "", "error": ""})
    app.run(debug=False)  # Disable debug to reduce Flask output