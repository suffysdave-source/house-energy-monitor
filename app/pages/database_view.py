from __future__ import annotations
import os
import sys
import logging
import psycopg2
from dash import html, dcc, dash_table, callback, Input, Output, register_page
from utils.config import load_config

# Adjust Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

register_page(__name__, path="/database-view", name="Database View")

# Logging setup
def setup_logging(config):
    """Configure logging with settings from config.json."""
    logger = logging.getLogger("house_energy")
    log_level = config.get("log_level", "WARNING").upper()
    logger.setLevel(getattr(logging, log_level, logging.WARNING))
    logger.handlers.clear()

    structured = config.get("structured", False)
    if structured:
        fmt = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "device_id": "%(device_id)s", "error": "%(error)s"}',
            "%Y-%m-%d %H:%M:%S"
        )
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

# Database queries
def get_tables(config, log):
    """Retrieve list of tables in the database."""
    try:
        conn = psycopg2.connect(
            host=config["database"]["host"],
            port=config["database"]["port"],
            dbname=config["database"]["name"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            connect_timeout=5
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cur.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        log.error(f"Failed to retrieve tables: {e}", extra={"device_id": "", "error": str(e)})
        return []

def get_columns(config, log, table_name):
    """Retrieve column names for the specified table."""
    try:
        conn = psycopg2.connect(
            host=config["database"]["host"],
            port=config["database"]["port"],
            dbname=config["database"]["name"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            connect_timeout=5
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,)
            )
            columns = [row[0] for row in cur.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        log.error(f"Failed to retrieve columns for {table_name}: {e}", extra={"device_id": "", "error": str(e)})
        return []

def get_last_readings(config, log, table_name, limit=20):
    """Retrieve the last 'limit' rows from the specified table."""
    try:
        conn = psycopg2.connect(
            host=config["database"]["host"],
            port=config["database"]["port"],
            dbname=config["database"]["name"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            connect_timeout=5
        )
        with conn.cursor() as cur:
            columns = get_columns(config, log, table_name)
            if not columns:
                return []
            # Sanitize table name to prevent SQL injection
            if not table_name.isalnum():
                log.error(f"Invalid table name: {table_name}", extra={"device_id": "", "error": "Invalid table name"})
                return []
            query = f"SELECT {', '.join(columns)} FROM {table_name} ORDER BY "
            # Assume tables have a timestamp or id column for ordering
            if "timestamp" in columns:
                query += "timestamp DESC"
            elif "id" in columns:
                query += "id DESC"
            else:
                query += columns[0] + " DESC"
            query += " LIMIT %s"
            cur.execute(query, (limit,))
            rows = cur.fetchall()
            # Format rows as dictionaries, handling timestamp and list formatting
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    if isinstance(row[i], (int, float)):
                        row_dict[col] = row[i]
                    elif col == "timestamp" and row[i]:
                        row_dict[col] = row[i].strftime("%Y-%m-%d %H:%M:%S")
                    elif col == "supports" and isinstance(row[i], list):
                        row_dict[col] = ", ".join(row[i])
                    else:
                        row_dict[col] = str(row[i]) if row[i] is not None else None
                data.append(row_dict)
        conn.close()
        return data
    except Exception as e:
        log.error(f"Failed to query table {table_name}: {e}", extra={"device_id": "", "error": str(e)})
        return []

# Layout
config = load_config()
log = setup_logging(config.get("logging", {}))
tables = get_tables(config, log)
default_table = "readings" if "readings" in tables else tables[0] if tables else None

layout = html.Div(
    style={"padding": "20px", "max-width": "800px", "margin": "auto"},
    children=[
        html.H2("Database View", style={"text-align": "center"}),
        html.P("Select a table to view the last 20 entries", style={"text-align": "center"}),
        html.Div(id="db-error", style={"color": "red", "text-align": "center", "marginBottom": "10px"}),
        html.Div(
            children=[
                html.Label("Select Table", style={"marginRight": "10px"}),
                dcc.Dropdown(
                    id="table-select",
                    options=[{"label": table, "value": table} for table in tables] if tables else [],
                    value=default_table,
                    style={"width": "200px", "display": "inline-block"},
                    placeholder="No tables available" if not tables else None
                ),
                html.Button("Refresh", id="refresh-table", n_clicks=0, style={"marginLeft": "10px", "padding": "5px"}),
            ],
            style={"text-align": "center", "marginBottom": "20px"}
        ),
        dash_table.DataTable(
            id="data-table",
            columns=[],
            data=[],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "5px"},
            style_header={"backgroundColor": "#f0f0f0", "fontWeight": "bold"},
            sort_action="native",
            page_size=20
        )
    ]
)

# Callback to update table data
@callback(
    [
        Output("data-table", "columns"),
        Output("data-table", "data"),
        Output("db-error", "children")
    ],
    [
        Input("table-select", "value"),
        Input("refresh-table", "n_clicks")
    ],
    prevent_initial_call=False
)
def update_table(table_name, n_clicks):
    if not table_name:
        return [], [], "No tables found in the database"
    columns = get_columns(config, log, table_name)
    if not columns:
        return [], [], f"Failed to retrieve columns for {table_name}"
    data = get_last_readings(config, log, table_name)
    if not data and not columns:
        return [], [], f"Failed to query table {table_name}"
    table_columns = [{"name": col, "id": col} for col in columns]
    return table_columns, data, ""