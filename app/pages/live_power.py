# File: live_power.py
# Description: Displays real-time power usage (active_power_w in Watts) for all active devices, polling from device APIs at intervals defined in config.json. Shows a single trace per device (positive for import, negative for export) with device-specific colors from config.json, using spline smoothing for graph lines, maintaining true historical data over a configurable time window. Includes a Last Updated timestamp and logs failed API calls and errors.
# Version: 1.8
# Author: Grok (generated for Dave)
# Created: 2025-10-19
# Last Modified: 2025-10-19

from __future__ import annotations
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html, callback, Input, Output, State, register_page
import requests

register_page(__name__, path="/live-power", name="Live Power")

# ---------- Config loading ----------
CONFIG_PATHS = [
    "/home/dave/projects/house/config/config.json",
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json"),
]

def _load_config() -> Dict:
    for p in CONFIG_PATHS:
        try:
            with open(os.path.abspath(p), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config from {p}: {str(e)}")
            continue
    return {}

CONFIG = _load_config()
POLLING_INTERVAL_SECONDS = CONFIG.get("polling", {}).get("interval_seconds", 2)
GRAPH_TIME_RANGE_MINUTES = CONFIG.get("polling", {}).get("graph_time_range_minutes", 5)

# ---------- Logging setup ----------
LOG_FILE = CONFIG.get("logging", {}).get("log_file", "/home/dave/projects/house/logs/energy.log")
if CONFIG.get("logging", {}).get("enabled", False):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

# ---------- Data fetcher ----------
def _fetch_api_data(device_id: str) -> Dict:
    device = CONFIG.get("devices", {}).get(device_id, {})
    ip = device.get("ip")
    port = device.get("port", 80)
    api_path = device.get("api_path", "/api/v1")
    if not ip or not api_path:
        logging.error(f"Invalid configuration for device {device_id}: missing ip or api_path")
        return {}
    api_url = f"http://{ip}:{port}{api_path}/data"
    try:
        response = requests.get(api_url, timeout=1)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to fetch data from {api_url}: {str(e)}")
        return {}

def _fetch_live_power() -> pd.DataFrame:
    """
    Fetch LIVE power data from device APIs only (no database storage).
    Returns a DataFrame with current readings for all active devices.
    """
    data = []
    current_time = datetime.now()
    
    for device_id, device in CONFIG.get("devices", {}).items():
        if not device.get("active", False):
            continue
        api_data = _fetch_api_data(device_id)
        if api_data:
            try:
                power_w = float(api_data.get("active_power_w", 0))
                data.append({
                    "ts": current_time,
                    "device_id": device_id,
                    "active_power_w": power_w
                })
            except (ValueError, TypeError) as e:
                logging.error(f"Failed to parse active_power_w for device {device_id}: {str(e)}")
    
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["ts", "device_id", "active_power_w"])
    df["ts"] = pd.to_datetime(df["ts"])
    return df

# ---------- Layout ----------
layout = html.Div(
    style={"padding": "20px"},
    children=[
        html.H2("Live Power Usage"),
        html.P(id="last-updated", children="Last Updated: Not yet updated"),
        html.P(f"Real-time power consumption (positive) and export (negative) for all devices (updates every {POLLING_INTERVAL_SECONDS} seconds)"),
        html.Div(
            style={"marginBottom": "15px"},
            children=[
                dcc.Dropdown(
                    id="live-power-device",
                    options=[{"label": "All Devices", "value": "all"}] + [
                        {"label": dev.get("name", dev_id), "value": dev_id}
                        for dev_id, dev in CONFIG.get("devices", {}).items()
                        if dev.get("active", False)
                    ],
                    value="all",
                    clearable=False,
                    style={"width": "250px"},
                ),
                dcc.Interval(id="live-power-interval", interval=POLLING_INTERVAL_SECONDS*1000, n_intervals=0),  # Update every 2 seconds
            ],
        ),
        dcc.Graph(id="live-power-graph"),
        dcc.Store(id="live-power-store-data", data=[]),  # Initialize with empty list
    ],
)

# ---------- Callbacks ----------
@callback(
    Output("live-power-store-data", "data"),
    Output("last-updated", "children"),
    Input("live-power-interval", "n_intervals"),
    State("live-power-store-data", "data"),
    prevent_initial_call=False
)
def _update_live_data(n_intervals, existing_data):
    """
    Append new power readings to the stored history, trim to the last configured time range, and update the Last Updated timestamp.
    """
    try:
        # Convert existing data to DataFrame
        df_existing = pd.DataFrame(existing_data)
        if not df_existing.empty:
            df_existing["ts"] = pd.to_datetime(df_existing["ts"])
        
        # Fetch new data
        df_new = _fetch_live_power()
        
        # Append new data to existing
        df = pd.concat([df_existing, df_new], ignore_index=True)
        
        # Trim to last configured time range
        cutoff_time = datetime.now() - timedelta(minutes=GRAPH_TIME_RANGE_MINUTES)
        df = df[df["ts"] >= cutoff_time]
        
        # Update timestamp
        last_updated = f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return df.to_dict("records"), last_updated
    except Exception as e:
        logging.error(f"Error in _update_live_data: {str(e)}")
        # Return existing data and current timestamp to prevent callback failure
        return existing_data, f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Error: {str(e)})"

@callback(
    Output("live-power-graph", "figure"),
    Input("live-power-store-data", "data"),
    Input("live-power-device", "value"),
    prevent_initial_call=False
)
def _render_live_graph(store, device):
    if not store:
        fig = go.Figure()
        fig.update_layout(
            title="No data available",
            xaxis_title="Time",
            yaxis_title="Power (W)",
            template="plotly_white"
        )
        return fig
    
    df = pd.DataFrame(store)
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="No data available",
            xaxis_title="Time",
            yaxis_title="Power (W)",
            template="plotly_white"
        )
        return fig

    df["ts"] = pd.to_datetime(df["ts"])
    if device != "all":
        df = df[df["device_id"] == device]
    
    fig = go.Figure()
    devices = df["device_id"].unique()
    
    for device_id in devices:
        df_dev = df[df["device_id"] == device_id].sort_values("ts")
        device_name = CONFIG.get("devices", {}).get(device_id, {}).get("name", device_id)
        device_color = CONFIG.get("devices", {}).get(device_id, {}).get("color", "#000000")  # Default to black
        
        fig.add_trace(go.Scatter(
            x=df_dev["ts"],
            y=df_dev["active_power_w"],
            name=device_name,
            line=dict(color=device_color, width=3, shape="spline"),  # Use spline smoothing
            mode="lines",  # Ensure continuous lines
            legendgroup=device_id,
            showlegend=True
        ))

    fig.update_layout(
        title=f"Live Power Usage (Last {GRAPH_TIME_RANGE_MINUTES} Minutes)",
        xaxis_title="Time",
        yaxis_title="Power (W)",
        legend_title="Device",
        hovermode="x unified",
        height=500,
        template="plotly_white"
    )
    
    # Auto-range y-axis to show from -max_export to +max_import
    if not df.empty:
        max_import = df["active_power_w"].clip(lower=0).max()
        max_export = abs(df["active_power_w"].clip(upper=0).min())
        y_range = max(max_import, max_export, 10) * 1.1  # Ensure at least ±10W range
        fig.update_yaxes(range=[-y_range, y_range])
    
    return fig