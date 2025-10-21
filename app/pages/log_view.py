from __future__ import annotations
import os
import sys
import json
import logging
from dash import html, dcc, dash_table, callback, Input, Output, register_page
from utils.config import load_config

# Adjust Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

register_page(__name__, path="/log-view", name="Log View")

# Logging setup
def setup_logging(config):
    """Configure logging with settings from config.json."""
    logger = logging.getLogger("house_energy")
    log_level = config.get("log_level", "WARNING").upper()
    logger.setLevel(getattr(logging, log_level, logging.WARNING))
    logger.handlers.clear()

    structured = config.get("structured", False)
    if structured:
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                    "level": record.levelname,
                    "message": record.msg,
                    "device_id": getattr(record, "device_id", ""),
                    "error": getattr(record, "error", "")
                }
                return json.dumps(log_entry)
        fmt = JsonFormatter()
    else:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    log_file = config.get("log_file")
    if config.get("enabled", True) and log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        max_bytes = config.get("max_bytes", 5 * 1024 * 1024)
        backup_count = config.get("backup_count", 3)
        time_based = config.get("time_based_rotation", False)
        if time_based:
            from logging.handlers import TimedRotatingFileHandler
            fh = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=backup_count)
        else:
            from logging.handlers import RotatingFileHandler
            fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger

# Log file parsing
def parse_log_file(config, log, limit=100):
    """Parse the log file and return the last 'limit' entries in reverse order (newest first)."""
    log_file = config.get("logging", {}).get("log_file", "/home/dave/projects/house/logs/energy.log")
    structured = config.get("logging", {}).get("structured", False)
    entries = []
    max_display_length = 50  # Truncate long fields for display

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]  # Read last 'limit' lines
        for line in lines:
            entry = {}
            line = line.strip()
            if not line:
                continue
            if structured:
                try:
                    # Try parsing as JSON
                    json_data = json.loads(line)
                    message = json_data.get("message", "")
                    error = json_data.get("error", "")
                    entry = {
                        "time": json_data.get("time", ""),
                        "level": json_data.get("level", ""),
                        "message": (message[:max_display_length] + "...") if len(message) > max_display_length else message,
                        "message_full": message,  # Store full text for tooltip
                        "device_id": json_data.get("device_id", ""),
                        "error": (error[:max_display_length] + "...") if len(error) > max_display_length else error,
                        "error_full": error  # Store full text for tooltip
                    }
                except json.JSONDecodeError:
                    # Fallback to unstructured parsing
                    parts = line.split(" | ", 2)
                    if len(parts) >= 3:
                        message = parts[2]
                        device_id = ""
                        error = ""
                        if "[" in parts[2] and "]" in parts[2]:
                            device_id = parts[2].split("[")[1].split("]")[0]
                            message = parts[2].replace(f"[{device_id}] ", "")
                        if "failed" in parts[2].lower() or "error" in parts[2].lower():
                            error = parts[2]
                        entry = {
                            "time": parts[0],
                            "level": parts[1],
                            "message": (message[:max_display_length] + "...") if len(message) > max_display_length else message,
                            "message_full": message,
                            "device_id": device_id,
                            "error": (error[:max_display_length] + "...") if len(error) > max_display_length else error,
                            "error_full": error
                        }
                    else:
                        entry = {
                            "time": "",
                            "level": "",
                            "message": (line[:max_display_length] + "...") if len(line) > max_display_length else line,
                            "message_full": line,
                            "device_id": "",
                            "error": "",
                            "error_full": ""
                        }
            else:
                # Unstructured parsing
                parts = line.split(" | ", 2)
                if len(parts) >= 3:
                    message = parts[2]
                    device_id = ""
                    error = ""
                    if "[" in parts[2] and "]" in parts[2]:
                        device_id = parts[2].split("[")[1].split("]")[0]
                        message = parts[2].replace(f"[{device_id}] ", "")
                    if "failed" in parts[2].lower() or "error" in parts[2].lower():
                        error = parts[2]
                    entry = {
                        "time": parts[0],
                        "level": parts[1],
                        "message": (message[:max_display_length] + "...") if len(message) > max_display_length else message,
                        "message_full": message,
                        "device_id": device_id,
                        "error": (error[:max_display_length] + "...") if len(error) > max_display_length else error,
                        "error_full": error
                    }
                else:
                    entry = {
                        "time": "",
                        "level": "",
                        "message": (line[:max_display_length] + "...") if len(line) > max_display_length else line,
                        "message_full": line,
                        "device_id": "",
                        "error": "",
                        "error_full": ""
                    }
            if entry:
                entries.append(entry)
    except Exception as e:
        log.error(f"Failed to read log file {log_file}: {e}", extra={"device_id": "", "error": str(e)})
        return []
    return entries[::-1]  # Reverse to show newest entries first

# Layout
config = load_config()
log = setup_logging(config.get("logging", {}))
layout = html.Div(
    style={"padding": "20px", "max-width": "800px", "margin": "auto"},
    children=[
        html.H2("Log View", style={"text-align": "center"}),
        html.P("Last 100 entries from energy.log (newest first)", style={"text-align": "center"}),
        html.Div(
            children=[
                html.Button("Refresh", id="refresh-log", n_clicks=0, style={"padding": "5px"}),
            ],
            style={"text-align": "center", "marginBottom": "20px"}
        ),
        html.Div(id="log-error", style={"color": "red", "text-align": "center", "marginBottom": "10px"}),
        dash_table.DataTable(
            id="log-table",
            columns=[
                {"name": "Time", "id": "time"},
                {"name": "Level", "id": "level"},
                {"name": "Message", "id": "message"},
                {"name": "Device ID", "id": "device_id"},
                {"name": "Error", "id": "error"}
            ],
            data=parse_log_file(config, log),
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "5px",
                "whiteSpace": "normal",
                "height": "auto",
                "minWidth": "50px",
                "maxWidth": "200px",
                "overflow": "hidden",
                "textOverflow": "ellipsis"
            },
            style_header={
                "backgroundColor": "#f0f0f0",
                "fontWeight": "bold",
                "whiteSpace": "normal",
                "height": "auto"
            },
            style_data_conditional=[
                {
                    "if": {"column_id": "message"},
                    "tooltip": {"value": "{message_full}", "use_with": "data"}
                },
                {
                    "if": {"column_id": "error"},
                    "tooltip": {"value": "{error_full}", "use_with": "data"}
                }
            ],
            sort_action="native",
            page_size=100,
            tooltip_data=[
                {
                    "message": {"value": entry["message_full"], "type": "text"},
                    "error": {"value": entry["error_full"], "type": "text"}
                } for entry in parse_log_file(config, log)
            ]
        )
    ]
)

# Callback to update log table
@callback(
    [
        Output("log-table", "data"),
        Output("log-table", "tooltip_data"),
        Output("log-error", "children")
    ],
    Input("refresh-log", "n_clicks"),
    prevent_initial_call=False
)
def update_log_table(n_clicks):
    data = parse_log_file(config, log)
    if not data:
        return [], [], "Failed to load log file"
    tooltip_data = [
        {
            "message": {"value": entry["message_full"], "type": "text"},
            "error": {"value": entry["error_full"], "type": "text"}
        } for entry in data
    ]
    return data, tooltip_data, ""