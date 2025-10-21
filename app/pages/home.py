# File: home.py
# Description: Home page with a summary of latest energy readings and costs, plus a chart for all active devices.
# Version: 1.3
# Author: Dave (optimized with Grok)
# Created: 2025-10-19
# Last Modified: 2025-10-20

from dash import html, dcc, register_page
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from utils.config import load_config

register_page(__name__, path="/", name="Home")

CONFIG = load_config()
DB_CONF = CONFIG.get("database", {})
TARIFFS = CONFIG.get("tariffs", {})
ENGINE = create_engine(
    f"postgresql://{DB_CONF['user']}:{DB_CONF['password']}@{DB_CONF['host']}:{DB_CONF['port']}/{DB_CONF['name']}",
    pool_size=5, max_overflow=10, pool_timeout=30, pool_pre_ping=True
)

def get_summary_data():
    start = datetime.now() - timedelta(minutes=CONFIG.get("polling", {}).get("graph_time_range_minutes", 10))
    devices = CONFIG.get("devices", {})
    dfs = []
    for device_id, device in devices.items():
        if not device.get("active", False):
            continue
        supports = device.get("supports", [])
        select_cols = ["timestamp AS ts"]
        if "import_kwh" in supports:
            select_cols.append("COALESCE(total_import_kwh, 0) AS import_kwh")
        if "export_kwh" in supports:
            select_cols.append("COALESCE(total_export_kwh, 0) AS export_kwh")
        if "gas_m3" in supports:
            select_cols.append("COALESCE(total_gas_m3, 0) AS gas_m3")
        query = text(f"SELECT {', '.join(select_cols)} FROM readings WHERE timestamp >= :start AND device_id = :device_id ORDER BY ts DESC LIMIT 1")
        with ENGINE.connect() as conn:
            df = pd.read_sql_query(query, conn, params={"start": start, "device_id": device_id})
            df["device"] = device.get("name", device_id)
            df["import_cost"] = df["import_kwh"] * TARIFFS.get("import_eur_per_kwh", 0.40) if "import_kwh" in df else 0
            df["export_cost"] = df["export_kwh"] * TARIFFS.get("export_eur_per_kwh", 0.04) if "export_kwh" in df else 0
            df["gas_cost"] = df["gas_m3"] * TARIFFS.get("gas_eur_per_m3", 0.80) if "gas_m3" in df else 0
        dfs.append(df)
    return pd.concat(dfs) if dfs else pd.DataFrame()

def get_summary_chart():
    start = datetime.now() - timedelta(minutes=CONFIG.get("polling", {}).get("graph_time_range_minutes", 10))
    devices = CONFIG.get("devices", {})
    dfs = []
    for device_id, device in devices.items():
        if not device.get("active", False):
            continue
        supports = device.get("supports", [])
        select_cols = ["timestamp AS ts"]
        if "import_kwh" in supports:
            select_cols.append("COALESCE(total_import_kwh, 0) AS import_kwh")
        if "export_kwh" in supports:
            select_cols.append("COALESCE(total_export_kwh, 0) AS export_kwh")
        if "gas_m3" in supports:
            select_cols.append("COALESCE(total_gas_m3, 0) AS gas_m3")
        query = text(f"SELECT {', '.join(select_cols)} FROM readings WHERE timestamp >= :start AND device_id = :device_id ORDER BY ts")
        with ENGINE.connect() as conn:
            df = pd.read_sql_query(query, conn, params={"start": start, "device_id": device_id})
            df["device"] = device.get("name", device_id)
            df["import_kwh"] = df["import_kwh"].diff().clip(lower=0).fillna(0) if "import_kwh" in df else 0
            df["export_kwh"] = -df["export_kwh"].diff().clip(lower=0).fillna(0) if "export_kwh" in df else 0
            df["gas_m3"] = df["gas_m3"].diff().clip(lower=0).fillna(0) if "gas_m3" in df else 0
        dfs.append(df)
    df = pd.concat(dfs) if dfs else pd.DataFrame()
    if df.empty:
        return px.line(title="No data available")
    fig = px.line(
        df, x="ts", y=["import_kwh", "export_kwh", "gas_m3"], color="device",
        labels={"ts": "Time", "value": "Value (kWh/m³)"},
        title=f"Recent Energy Usage (Last {CONFIG.get('polling', {}).get('graph_time_range_minutes', 10)} Minutes)",
        color_discrete_map={
            device.get("name", device_id): device.get("color", "#000000") for device_id, device in devices.items()
        }
    )
    fig.update_layout(autosize=True, hovermode="x unified")
    return fig

df = get_summary_data()
layout = html.Div(
    style={"padding": "20px", "max-width": "1200px", "margin": "auto"},
    children=[
        html.H2("House Energy Monitor Dashboard"),
        dcc.Loading([
            dcc.Graph(figure=get_summary_chart()),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(150px, 1fr))", "gap": "10px", "margin": "10px 0"},
                children=[
                    html.Div([
                        html.P(device.get("name", device_id)),
                        html.P(f"Import: {df[df['device'] == device.get('name', device_id)].iloc[-1].get('import_kwh', 0):.2f} kWh, €{df[df['device'] == device.get('name', device_id)].iloc[-1].get('import_cost', 0):.2f}"),
                        html.P(f"Export: {df[df['device'] == device.get('name', device_id)].iloc[-1].get('export_kwh', 0):.2f} kWh, €{df[df['device'] == device.get('name', device_id)].iloc[-1].get('export_cost', 0):.2f}"),
                        html.P(f"Gas: {df[df['device'] == device.get('name', device_id)].iloc[-1].get('gas_m3', 0):.2f} m³, €{df[df['device'] == device.get('name', device_id)].iloc[-1].get('gas_cost', 0):.2f}") if "gas_m3" in device.get("supports", []) else html.P("Gas: —")
                    ])
                    for device_id, device in CONFIG.get("devices", {}).items() if device.get("active", False)
                ]
            )
        ])
    ]
)