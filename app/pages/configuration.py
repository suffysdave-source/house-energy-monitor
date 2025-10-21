from __future__ import annotations
import os
import json
import re
from dash import html, dcc, callback, Input, Output, State, register_page, no_update
from dash.exceptions import PreventUpdate
import dash

register_page(__name__, path="/configuration", name="Configuration")

# ---------- Config loading and defaults ----------
CONFIG_PATH = "/home/dave/projects/house/config/config.json"
DEFAULT_CONFIG = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "house_energy_db",
        "user": "dave",
        "password": "energy123"
    },
    "devices": {
        "main_meter": {
            "name": "Main Energy Meter",
            "ip": "192.168.0.240",
            "port": 80,
            "api_path": "/api/v1",
            "supports": ["import_kwh", "export_kwh", "gas_m3"],
            "active": True,
            "color": "#FFA500"
        },
        "kwh_meter": {
            "name": "kWh Meter",
            "ip": "192.168.0.242",
            "port": 80,
            "api_path": "/api/v1",
            "supports": ["import_kwh", "export_kwh"],
            "active": True,
            "color": "#FFFF00"
        },
        "energy_socket_1": {
            "name": "Energy Socket 1",
            "ip": "192.168.0.241",
            "port": 80,
            "api_path": "/api/v1",
            "supports": ["import_kwh", "export_kwh"],
            "active": True,
            "color": "#8B4513"
        }
    },
    "polling": {
        "interval_seconds": 60,
        "graph_time_range_minutes": 5
    },
    "logging": {
        "enabled": True,
        "log_file": "/home/dave/projects/house/logs/energy.log",
        "log_level": "WARNING",
        "structured": True,
        "max_bytes": 5242880,
        "backup_count": 3,
        "time_based_rotation": False
    },
    "tariffs": {
        "import_eur_per_kwh": 0.3745,
        "export_eur_per_kwh": 0.031824,
        "gas_eur_per_m3": 0.84077
    }
}

def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config from {CONFIG_PATH}: {e}")
        return DEFAULT_CONFIG

def _save_config(config: dict) -> tuple[bool, str]:
    try:
        config_dir = os.path.dirname(CONFIG_PATH)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True, "Configuration saved successfully!"
    except Exception as e:
        error_msg = f"Error saving config to {CONFIG_PATH}: {e}"
        print(error_msg)
        return False, error_msg

def validate_ip(ip: str) -> bool:
    """Validate IPv4 address."""
    pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    return bool(re.match(pattern, ip)) if ip else False

def validate_positive_number(value, min_value=0) -> bool:
    """Validate positive number."""
    try:
        return float(value) >= min_value if value is not None else False
    except (ValueError, TypeError):
        return False

def validate_supports(supports: list) -> bool:
    """Validate supports field."""
    valid_supports = ["import_kwh", "export_kwh", "gas_m3"]
    return bool(supports) and all(item in valid_supports for item in supports)

def validate_hex_color(color: str) -> bool:
    """Validate hex color code."""
    pattern = r"^#[0-9A-Fa-f]{6}$"
    return bool(re.match(pattern, color)) if color else False

# ---------- Layout ----------
layout = html.Div(
    style={"padding": "20px", "max-width": "800px", "margin": "auto"},
    children=[
        html.H2("Configuration", style={"text-align": "center"}),
        dcc.Tabs([
            dcc.Tab(label="Database", children=[
                html.Div([
                    html.Label("Host", title="Database server address"),
                    dcc.Input(id="db-host", type="text", placeholder="e.g., localhost", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="db-host-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Port", title="Database server port"),
                    dcc.Input(id="db-port", type="number", placeholder="e.g., 5432", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="db-port-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Database Name", title="Name of the database"),
                    dcc.Input(id="db-name", type="text", placeholder="e.g., house_energy_db", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="db-name-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("User", title="Database user"),
                    dcc.Input(id="db-user", type="text", placeholder="e.g., dave", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="db-user-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Password", title="Database password"),
                    dcc.Input(id="db-password", type="password", placeholder="e.g., energy123", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="db-password-error", style={"color": "red", "fontSize": "12px"}),
                ], style={"padding": "15px"})
            ]),
            dcc.Tab(label="Devices", children=[
                html.Div([
                    html.H4("Main Energy Meter"),
                    html.Label("Name", title="Device display name"),
                    dcc.Input(id="main-meter-name", type="text", placeholder="e.g., Main Energy Meter", style={"width": "100%", "marginBottom": "10px"}),
                    html.Label("IP", title="Device IP address"),
                    dcc.Input(id="main-meter-ip", type="text", placeholder="e.g., 192.168.0.240", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="main-meter-ip-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Port", title="Device port"),
                    dcc.Input(id="main-meter-port", type="number", placeholder="e.g., 80", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="main-meter-port-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("API Path", title="Device API endpoint"),
                    dcc.Input(id="main-meter-api-path", type="text", placeholder="e.g., /api/v1", style={"width": "100%", "marginBottom": "10px"}),
                    html.Label("Supports", title="Supported metrics (select multiple)"),
                    dcc.Dropdown(
                        id="main-meter-supports",
                        options=[{"label": x, "value": x} for x in ["import_kwh", "export_kwh", "gas_m3"]],
                        multi=True,
                        style={"width": "100%", "marginBottom": "10px"}
                    ),
                    html.Div(id="main-meter-supports-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Active", title="Enable/disable device"),
                    dcc.Checklist(id="main-meter-active", options=[{"label": "Active", "value": "true"}], style={"marginBottom": "10px"}),
                    html.Label("Color", title="Graph color (hex code, e.g., #FFA500)"),
                    dcc.Input(id="main-meter-color", type="text", placeholder="e.g., #FFA500", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="main-meter-color-error", style={"color": "red", "fontSize": "12px"}),
                    html.H4("kWh Meter"),
                    html.Label("Name"),
                    dcc.Input(id="kwh-meter-name", type="text", placeholder="e.g., kWh Meter", style={"width": "100%", "marginBottom": "10px"}),
                    html.Label("IP"),
                    dcc.Input(id="kwh-meter-ip", type="text", placeholder="e.g., 192.168.0.242", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="kwh-meter-ip-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Port"),
                    dcc.Input(id="kwh-meter-port", type="number", placeholder="e.g., 80", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="kwh-meter-port-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("API Path"),
                    dcc.Input(id="kwh-meter-api-path", type="text", placeholder="e.g., /api/v1", style={"width": "100%", "marginBottom": "10px"}),
                    html.Label("Supports"),
                    dcc.Dropdown(
                        id="kwh-meter-supports",
                        options=[{"label": x, "value": x} for x in ["import_kwh", "export_kwh", "gas_m3"]],
                        multi=True,
                        style={"width": "100%", "marginBottom": "10px"}
                    ),
                    html.Div(id="kwh-meter-supports-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Active"),
                    dcc.Checklist(id="kwh-meter-active", options=[{"label": "Active", "value": "true"}], style={"marginBottom": "10px"}),
                    html.Label("Color", title="Graph color (hex code, e.g., #FFFF00)"),
                    dcc.Input(id="kwh-meter-color", type="text", placeholder="e.g., #FFFF00", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="kwh-meter-color-error", style={"color": "red", "fontSize": "12px"}),
                    html.H4("Energy Socket 1"),
                    html.Label("Name"),
                    dcc.Input(id="socket-1-name", type="text", placeholder="e.g., Energy Socket 1", style={"width": "100%", "marginBottom": "10px"}),
                    html.Label("IP"),
                    dcc.Input(id="socket-1-ip", type="text", placeholder="e.g., 192.168.0.241", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="socket-1-ip-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Port"),
                    dcc.Input(id="socket-1-port", type="number", placeholder="e.g., 80", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="socket-1-port-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("API Path"),
                    dcc.Input(id="socket-1-api-path", type="text", placeholder="e.g., /api/v1", style={"width": "100%", "marginBottom": "10px"}),
                    html.Label("Supports"),
                    dcc.Dropdown(
                        id="socket-1-supports",
                        options=[{"label": x, "value": x} for x in ["import_kwh", "export_kwh", "gas_m3"]],
                        multi=True,
                        style={"width": "100%", "marginBottom": "10px"}
                    ),
                    html.Div(id="socket-1-supports-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Active"),
                    dcc.Checklist(id="socket-1-active", options=[{"label": "Active", "value": "true"}], style={"marginBottom": "10px"}),
                    html.Label("Color", title="Graph color (hex code, e.g., #8B4513)"),
                    dcc.Input(id="socket-1-color", type="text", placeholder="e.g., #8B4513", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="socket-1-color-error", style={"color": "red", "fontSize": "12px"}),
                ], style={"padding": "15px"})
            ]),
            dcc.Tab(label="Polling", children=[
                html.Div([
                    html.Label("Interval (seconds)", title="Polling interval for device data"),
                    dcc.Input(id="polling-interval", type="number", placeholder="e.g., 60", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="polling-interval-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Graph Time Range (minutes)", title="Time window for graphs"),
                    dcc.Input(id="polling-graph-range", type="number", placeholder="e.g., 5", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="polling-graph-range-error", style={"color": "red", "fontSize": "12px"}),
                ], style={"padding": "15px"})
            ]),
            dcc.Tab(label="Logging", children=[
                html.Div([
                    html.Label("Enabled", title="Enable/disable logging"),
                    dcc.Checklist(id="logging-enabled", options=[{"label": "Enabled", "value": "true"}], style={"marginBottom": "10px"}),
                    html.Label("Log File", title="Path to log file"),
                    dcc.Input(id="logging-file", type="text", placeholder="e.g., /home/dave/projects/house/logs/energy.log", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="logging-file-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Log Level", title="Logging verbosity level"),
                    dcc.Dropdown(
                        id="logging-level",
                        options=[
                            {"label": "DEBUG", "value": "DEBUG"},
                            {"label": "INFO", "value": "INFO"},
                            {"label": "WARNING", "value": "WARNING"},
                            {"label": "ERROR", "value": "ERROR"}
                        ],
                        value="WARNING",
                        style={"width": "100%", "marginBottom": "10px"}
                    ),
                    html.Label("Structured Logging", title="Enable JSON-like log format"),
                    dcc.Checklist(id="logging-structured", options=[{"label": "Enabled", "value": "true"}], style={"marginBottom": "10px"}),
                    html.Label("Max Bytes", title="Max size of log file before rotation"),
                    dcc.Input(id="logging-max-bytes", type="number", placeholder="e.g., 5242880", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="logging-max-bytes-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Backup Count", title="Number of backup log files"),
                    dcc.Input(id="logging-backup-count", type="number", placeholder="e.g., 3", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="logging-backup-count-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Time-Based Rotation", title="Rotate logs daily"),
                    dcc.Checklist(id="logging-time-based", options=[{"label": "Enabled", "value": "true"}], style={"marginBottom": "10px"}),
                ], style={"padding": "15px"})
            ]),
            dcc.Tab(label="Tariffs", children=[
                html.Div([
                    html.Label("Import (€/kWh)", title="Cost per kWh imported"),
                    dcc.Input(id="tariff-import", type="number", step=0.000001, placeholder="e.g., 0.3745", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="tariff-import-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Export (€/kWh)", title="Cost per kWh exported"),
                    dcc.Input(id="tariff-export", type="number", step=0.000001, placeholder="e.g., 0.031824", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="tariff-export-error", style={"color": "red", "fontSize": "12px"}),
                    html.Label("Gas (€/m³)", title="Cost per cubic meter of gas"),
                    dcc.Input(id="tariff-gas", type="number", step=0.000001, placeholder="e.g., 0.84077", style={"width": "100%", "marginBottom": "10px"}),
                    html.Div(id="tariff-gas-error", style={"color": "red", "fontSize": "12px"}),
                ], style={"padding": "15px"})
            ]),
        ]),
        html.Div([
            html.Button("Save Configuration", id="save-config", n_clicks=0, style={"padding": "10px", "marginRight": "10px"}),
            html.Button("Reset to Defaults", id="reset-config", n_clicks=0, style={"padding": "10px"}),
            dcc.Loading(
                id="loading-save",
                type="circle",
                children=html.Div(id="save-status", style={"marginTop": "10px", "color": "green"})
            ),
        ], style={"marginTop": "20px", "text-align": "center"}),
        dcc.Store(id="config-store", data={}),
        dcc.Interval(id="initial-load", interval=1, max_intervals=1, disabled=False),
        dcc.Interval(id="clear-status", interval=5000, max_intervals=1, disabled=True),
    ],
)

# ---------- Combined Callback ----------
@callback(
    [
        Output("db-host", "value"),
        Output("db-port", "value"),
        Output("db-name", "value"),
        Output("db-user", "value"),
        Output("db-password", "value"),
        Output("main-meter-name", "value"),
        Output("main-meter-ip", "value"),
        Output("main-meter-port", "value"),
        Output("main-meter-api-path", "value"),
        Output("main-meter-supports", "value"),
        Output("main-meter-active", "value"),
        Output("main-meter-color", "value"),
        Output("kwh-meter-name", "value"),
        Output("kwh-meter-ip", "value"),
        Output("kwh-meter-port", "value"),
        Output("kwh-meter-api-path", "value"),
        Output("kwh-meter-supports", "value"),
        Output("kwh-meter-active", "value"),
        Output("kwh-meter-color", "value"),
        Output("socket-1-name", "value"),
        Output("socket-1-ip", "value"),
        Output("socket-1-port", "value"),
        Output("socket-1-api-path", "value"),
        Output("socket-1-supports", "value"),
        Output("socket-1-active", "value"),
        Output("socket-1-color", "value"),
        Output("polling-interval", "value"),
        Output("polling-graph-range", "value"),
        Output("logging-enabled", "value"),
        Output("logging-file", "value"),
        Output("logging-level", "value"),
        Output("logging-structured", "value"),
        Output("logging-max-bytes", "value"),
        Output("logging-backup-count", "value"),
        Output("logging-time-based", "value"),
        Output("tariff-import", "value"),
        Output("tariff-export", "value"),
        Output("tariff-gas", "value"),
        Output("config-store", "data"),
        Output("save-status", "children"),
        Output("clear-status", "disabled"),
        Output("db-host-error", "children"),
        Output("db-port-error", "children"),
        Output("db-name-error", "children"),
        Output("db-user-error", "children"),
        Output("db-password-error", "children"),
        Output("main-meter-ip-error", "children"),
        Output("main-meter-port-error", "children"),
        Output("main-meter-supports-error", "children"),
        Output("main-meter-color-error", "children"),
        Output("kwh-meter-ip-error", "children"),
        Output("kwh-meter-port-error", "children"),
        Output("kwh-meter-supports-error", "children"),
        Output("kwh-meter-color-error", "children"),
        Output("socket-1-ip-error", "children"),
        Output("socket-1-port-error", "children"),
        Output("socket-1-supports-error", "children"),
        Output("socket-1-color-error", "children"),
        Output("polling-interval-error", "children"),
        Output("polling-graph-range-error", "children"),
        Output("logging-file-error", "children"),
        Output("logging-max-bytes-error", "children"),
        Output("logging-backup-count-error", "children"),
        Output("tariff-import-error", "children"),
        Output("tariff-export-error", "children"),
        Output("tariff-gas-error", "children"),
    ],
    [
        Input("initial-load", "n_intervals"),
        Input("save-config", "n_clicks"),
        Input("reset-config", "n_clicks"),
        Input("clear-status", "n_intervals"),
    ],
    [
        State("db-host", "value"),
        State("db-port", "value"),
        State("db-name", "value"),
        State("db-user", "value"),
        State("db-password", "value"),
        State("main-meter-name", "value"),
        State("main-meter-ip", "value"),
        State("main-meter-port", "value"),
        State("main-meter-api-path", "value"),
        State("main-meter-supports", "value"),
        State("main-meter-active", "value"),
        State("main-meter-color", "value"),
        State("kwh-meter-name", "value"),
        State("kwh-meter-ip", "value"),
        State("kwh-meter-port", "value"),
        State("kwh-meter-api-path", "value"),
        State("kwh-meter-supports", "value"),
        State("kwh-meter-active", "value"),
        State("kwh-meter-color", "value"),
        State("socket-1-name", "value"),
        State("socket-1-ip", "value"),
        State("socket-1-port", "value"),
        State("socket-1-api-path", "value"),
        State("socket-1-supports", "value"),
        State("socket-1-active", "value"),
        State("socket-1-color", "value"),
        State("polling-interval", "value"),
        State("polling-graph-range", "value"),
        State("logging-enabled", "value"),
        State("logging-file", "value"),
        State("logging-level", "value"),
        State("logging-structured", "value"),
        State("logging-max-bytes", "value"),
        State("logging-backup-count", "value"),
        State("logging-time-based", "value"),
        State("tariff-import", "value"),
        State("tariff-export", "value"),
        State("tariff-gas", "value"),
    ],
    prevent_initial_call=False,
)
def config_manager(
    n_intervals, save_clicks, reset_clicks, clear_intervals,
    db_host, db_port, db_name, db_user, db_password,
    main_meter_name, main_meter_ip, main_meter_port, main_meter_api_path, main_meter_supports, main_meter_active, main_meter_color,
    kwh_meter_name, kwh_meter_ip, kwh_meter_port, kwh_meter_api_path, kwh_meter_supports, kwh_meter_active, kwh_meter_color,
    socket_1_name, socket_1_ip, socket_1_port, socket_1_api_path, socket_1_supports, socket_1_active, socket_1_color,
    polling_interval, polling_graph_range,
    logging_enabled, logging_file, logging_level, logging_structured, logging_max_bytes, logging_backup_count, logging_time_based,
    tariff_import, tariff_export, tariff_gas
):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    config = _load_config()
    database = config.get("database", {})
    devices = config.get("devices", {})
    main_meter = devices.get("main_meter", {})
    kwh_meter = devices.get("kwh_meter", {})
    energy_socket_1 = devices.get("energy_socket_1", {})
    polling = config.get("polling", {})
    logging = config.get("logging", {})
    tariffs = config.get("tariffs", {})

    # Default output values for loading config
    outputs = (
        database.get("host", "localhost"),
        database.get("port", 5432),
        database.get("name", "house_energy_db"),
        database.get("user", "dave"),
        database.get("password", "energy123"),
        main_meter.get("name", "Main Energy Meter"),
        main_meter.get("ip", "192.168.0.240"),
        main_meter.get("port", 80),
        main_meter.get("api_path", "/api/v1"),
        main_meter.get("supports", ["import_kwh", "export_kwh", "gas_m3"]),
        ["true"] if main_meter.get("active", True) else [],
        main_meter.get("color", "#FFA500"),
        kwh_meter.get("name", "kWh Meter"),
        kwh_meter.get("ip", "192.168.0.242"),
        kwh_meter.get("port", 80),
        kwh_meter.get("api_path", "/api/v1"),
        kwh_meter.get("supports", ["import_kwh", "export_kwh"]),
        ["true"] if kwh_meter.get("active", True) else [],
        kwh_meter.get("color", "#FFFF00"),
        energy_socket_1.get("name", "Energy Socket 1"),
        energy_socket_1.get("ip", "192.168.0.241"),
        energy_socket_1.get("port", 80),
        energy_socket_1.get("api_path", "/api/v1"),
        energy_socket_1.get("supports", ["import_kwh", "export_kwh"]),
        ["true"] if energy_socket_1.get("active", True) else [],
        energy_socket_1.get("color", "#8B4513"),
        polling.get("interval_seconds", 60),
        polling.get("graph_time_range_minutes", 5),
        ["true"] if logging.get("enabled", True) else [],
        logging.get("log_file", "/home/dave/projects/house/logs/energy.log"),
        logging.get("log_level", "WARNING"),
        ["true"] if logging.get("structured", False) else [],
        logging.get("max_bytes", 5242880),
        logging.get("backup_count", 3),
        ["true"] if logging.get("time_based_rotation", False) else [],
        tariffs.get("import_eur_per_kwh", 0.3745),
        tariffs.get("export_eur_per_kwh", 0.031824),
        tariffs.get("gas_eur_per_m3", 0.84077),
        config,
        "",
        True,  # clear-status disabled
        "" if db_host else "Required",
        "" if validate_positive_number(db_port, 1) else "Must be positive",
        "" if db_name else "Required",
        "" if db_user else "Required",
        "" if db_password else "Required",
        "" if validate_ip(main_meter_ip) else "Invalid IP",
        "" if validate_positive_number(main_meter_port, 1) else "Must be positive",
        "" if validate_supports(main_meter_supports) else "Select at least one",
        "" if validate_hex_color(main_meter_color) else "Invalid hex color",
        "" if validate_ip(kwh_meter_ip) else "Invalid IP",
        "" if validate_positive_number(kwh_meter_port, 1) else "Must be positive",
        "" if validate_supports(kwh_meter_supports) else "Select at least one",
        "" if validate_hex_color(kwh_meter_color) else "Invalid hex color",
        "" if validate_ip(socket_1_ip) else "Invalid IP",
        "" if validate_positive_number(socket_1_port, 1) else "Must be positive",
        "" if validate_supports(socket_1_supports) else "Select at least one",
        "" if validate_hex_color(socket_1_color) else "Invalid hex color",
        "" if validate_positive_number(polling_interval, 1) else "Must be positive",
        "" if validate_positive_number(polling_graph_range, 1) else "Must be positive",
        "" if logging_file else "Required",
        "" if validate_positive_number(logging_max_bytes, 1024) else "Must be at least 1024",
        "" if validate_positive_number(logging_backup_count, 0) else "Must be non-negative",
        "" if validate_positive_number(tariff_import, 0) else "Must be non-negative",
        "" if validate_positive_number(tariff_export, 0) else "Must be non-negative",
        "" if validate_positive_number(tariff_gas, 0) else "Must be non-negative"
    )

    if triggered_id == "save-config" and save_clicks and save_clicks > 0:
        # Validate inputs
        errors = [
            "" if db_host else "Required",
            "" if validate_positive_number(db_port, 1) else "Must be positive",
            "" if db_name else "Required",
            "" if db_user else "Required",
            "" if db_password else "Required",
            "" if validate_ip(main_meter_ip) else "Invalid IP",
            "" if validate_positive_number(main_meter_port, 1) else "Must be positive",
            "" if validate_supports(main_meter_supports) else "Select at least one",
            "" if validate_hex_color(main_meter_color) else "Invalid hex color",
            "" if validate_ip(kwh_meter_ip) else "Invalid IP",
            "" if validate_positive_number(kwh_meter_port, 1) else "Must be positive",
            "" if validate_supports(kwh_meter_supports) else "Select at least one",
            "" if validate_hex_color(kwh_meter_color) else "Invalid hex color",
            "" if validate_ip(socket_1_ip) else "Invalid IP",
            "" if validate_positive_number(socket_1_port, 1) else "Must be positive",
            "" if validate_supports(socket_1_supports) else "Select at least one",
            "" if validate_hex_color(socket_1_color) else "Invalid hex color",
            "" if validate_positive_number(polling_interval, 1) else "Must be positive",
            "" if validate_positive_number(polling_graph_range, 1) else "Must be positive",
            "" if logging_file else "Required",
            "" if validate_positive_number(logging_max_bytes, 1024) else "Must be at least 1024",
            "" if validate_positive_number(logging_backup_count, 0) else "Must be non-negative",
            "" if validate_positive_number(tariff_import, 0) else "Must be non-negative",
            "" if validate_positive_number(tariff_export, 0) else "Must be non-negative",
            "" if validate_positive_number(tariff_gas, 0) else "Must be non-negative"
        ]
        if any(errors):
            return outputs[:-25] + (no_update, "Please fix validation errors", True) + tuple(errors)

        # Save operation
        new_config = {
            "database": {
                "host": db_host or "localhost",
                "port": int(db_port or 5432),
                "name": db_name or "house_energy_db",
                "user": db_user or "dave",
                "password": db_password or "energy123",
            },
            "devices": {
                "main_meter": {
                    "name": main_meter_name or "Main Energy Meter",
                    "ip": main_meter_ip or "192.168.0.240",
                    "port": int(main_meter_port or 80),
                    "api_path": main_meter_api_path or "/api/v1",
                    "supports": main_meter_supports or ["import_kwh", "export_kwh", "gas_m3"],
                    "active": main_meter_active == ["true"],
                    "color": main_meter_color or "#FFA500",
                },
                "kwh_meter": {
                    "name": kwh_meter_name or "kWh Meter",
                    "ip": kwh_meter_ip or "192.168.0.242",
                    "port": int(kwh_meter_port or 80),
                    "api_path": kwh_meter_api_path or "/api/v1",
                    "supports": kwh_meter_supports or ["import_kwh", "export_kwh"],
                    "active": kwh_meter_active == ["true"],
                    "color": kwh_meter_color or "#FFFF00",
                },
                "energy_socket_1": {
                    "name": socket_1_name or "Energy Socket 1",
                    "ip": socket_1_ip or "192.168.0.241",
                    "port": int(socket_1_port or 80),
                    "api_path": socket_1_api_path or "/api/v1",
                    "supports": socket_1_supports or ["import_kwh", "export_kwh"],
                    "active": socket_1_active == ["true"],
                    "color": socket_1_color or "#8B4513",
                },
            },
            "polling": {
                "interval_seconds": int(polling_interval or 60),
                "graph_time_range_minutes": int(polling_graph_range or 5),
            },
            "logging": {
                "enabled": logging_enabled == ["true"],
                "log_file": logging_file or "/home/dave/projects/house/logs/energy.log",
                "log_level": logging_level or "WARNING",
                "structured": logging_structured == ["true"],
                "max_bytes": int(logging_max_bytes or 5242880),
                "backup_count": int(logging_backup_count or 3),
                "time_based_rotation": logging_time_based == ["true"],
            },
            "tariffs": {
                "import_eur_per_kwh": float(tariff_import or 0.3745),
                "export_eur_per_kwh": float(tariff_export or 0.031824),
                "gas_eur_per_m3": float(tariff_gas or 0.84077),
            },
        }
        success, message = _save_config(new_config)
        if success:
            return (
                new_config["database"]["host"],
                new_config["database"]["port"],
                new_config["database"]["name"],
                new_config["database"]["user"],
                new_config["database"]["password"],
                new_config["devices"]["main_meter"]["name"],
                new_config["devices"]["main_meter"]["ip"],
                new_config["devices"]["main_meter"]["port"],
                new_config["devices"]["main_meter"]["api_path"],
                new_config["devices"]["main_meter"]["supports"],
                ["true"] if new_config["devices"]["main_meter"]["active"] else [],
                new_config["devices"]["main_meter"]["color"],
                new_config["devices"]["kwh_meter"]["name"],
                new_config["devices"]["kwh_meter"]["ip"],
                new_config["devices"]["kwh_meter"]["port"],
                new_config["devices"]["kwh_meter"]["api_path"],
                new_config["devices"]["kwh_meter"]["supports"],
                ["true"] if new_config["devices"]["kwh_meter"]["active"] else [],
                new_config["devices"]["kwh_meter"]["color"],
                new_config["devices"]["energy_socket_1"]["name"],
                new_config["devices"]["energy_socket_1"]["ip"],
                new_config["devices"]["energy_socket_1"]["port"],
                new_config["devices"]["energy_socket_1"]["api_path"],
                new_config["devices"]["energy_socket_1"]["supports"],
                ["true"] if new_config["devices"]["energy_socket_1"]["active"] else [],
                new_config["devices"]["energy_socket_1"]["color"],
                new_config["polling"]["interval_seconds"],
                new_config["polling"]["graph_time_range_minutes"],
                ["true"] if new_config["logging"]["enabled"] else [],
                new_config["logging"]["log_file"],
                new_config["logging"]["log_level"],
                ["true"] if new_config["logging"]["structured"] else [],
                new_config["logging"]["max_bytes"],
                new_config["logging"]["backup_count"],
                ["true"] if new_config["logging"]["time_based_rotation"] else [],
                new_config["tariffs"]["import_eur_per_kwh"],
                new_config["tariffs"]["export_eur_per_kwh"],
                new_config["tariffs"]["gas_eur_per_m3"],
                new_config,
                message,
                False,  # Enable clear-status
                *[""] * len(errors)  # Clear errors
            )
        return outputs[:-25] + (no_update, message, True) + tuple(errors)
    elif triggered_id == "reset-config" and reset_clicks and reset_clicks > 0:
        # Reset to defaults
        success, message = _save_config(DEFAULT_CONFIG)
        if success:
            return (
                DEFAULT_CONFIG["database"]["host"],
                DEFAULT_CONFIG["database"]["port"],
                DEFAULT_CONFIG["database"]["name"],
                DEFAULT_CONFIG["database"]["user"],
                DEFAULT_CONFIG["database"]["password"],
                DEFAULT_CONFIG["devices"]["main_meter"]["name"],
                DEFAULT_CONFIG["devices"]["main_meter"]["ip"],
                DEFAULT_CONFIG["devices"]["main_meter"]["port"],
                DEFAULT_CONFIG["devices"]["main_meter"]["api_path"],
                DEFAULT_CONFIG["devices"]["main_meter"]["supports"],
                ["true"] if DEFAULT_CONFIG["devices"]["main_meter"]["active"] else [],
                DEFAULT_CONFIG["devices"]["main_meter"]["color"],
                DEFAULT_CONFIG["devices"]["kwh_meter"]["name"],
                DEFAULT_CONFIG["devices"]["kwh_meter"]["ip"],
                DEFAULT_CONFIG["devices"]["kwh_meter"]["port"],
                DEFAULT_CONFIG["devices"]["kwh_meter"]["api_path"],
                DEFAULT_CONFIG["devices"]["kwh_meter"]["supports"],
                ["true"] if DEFAULT_CONFIG["devices"]["kwh_meter"]["active"] else [],
                DEFAULT_CONFIG["devices"]["kwh_meter"]["color"],
                DEFAULT_CONFIG["devices"]["energy_socket_1"]["name"],
                DEFAULT_CONFIG["devices"]["energy_socket_1"]["ip"],
                DEFAULT_CONFIG["devices"]["energy_socket_1"]["port"],
                DEFAULT_CONFIG["devices"]["energy_socket_1"]["api_path"],
                DEFAULT_CONFIG["devices"]["energy_socket_1"]["supports"],
                ["true"] if DEFAULT_CONFIG["devices"]["energy_socket_1"]["active"] else [],
                DEFAULT_CONFIG["devices"]["energy_socket_1"]["color"],
                DEFAULT_CONFIG["polling"]["interval_seconds"],
                DEFAULT_CONFIG["polling"]["graph_time_range_minutes"],
                ["true"] if DEFAULT_CONFIG["logging"]["enabled"] else [],
                DEFAULT_CONFIG["logging"]["log_file"],
                DEFAULT_CONFIG["logging"]["log_level"],
                ["true"] if DEFAULT_CONFIG["logging"]["structured"] else [],
                DEFAULT_CONFIG["logging"]["max_bytes"],
                DEFAULT_CONFIG["logging"]["backup_count"],
                ["true"] if DEFAULT_CONFIG["logging"]["time_based_rotation"] else [],
                DEFAULT_CONFIG["tariffs"]["import_eur_per_kwh"],
                DEFAULT_CONFIG["tariffs"]["export_eur_per_kwh"],
                DEFAULT_CONFIG["tariffs"]["gas_eur_per_m3"],
                DEFAULT_CONFIG,
                "Configuration reset to defaults!",
                False,
                *[""] * len(errors)  # Clear errors
            )
        return outputs[:-25] + (no_update, message, True) + tuple(errors)
    elif triggered_id == "clear-status" and clear_intervals and clear_intervals > 0:
        # Clear save-status
        return outputs[:-25] + (no_update, "", True) + tuple(outputs[-25:-3])
    elif triggered_id == "initial-load":
        # Load operation
        return outputs
    else:
        raise PreventUpdate