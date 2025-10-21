# File: device.py
# Description: Unified page for device energy usage with a dropdown to select devices, showing electricity, gas (if supported), and cost graphs, plus summary cards for totals.
# Version: 1.9
# Author: Dave (optimized with Grok)
# Created: 2025-10-20
# Last Modified: 2025-10-20

from dash import html, dcc, callback, Input, Output, register_page
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, date
from cachetools import TTLCache
from utils.config import load_config
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

CONFIG = load_config()
DB_CONF = CONFIG.get("database", {})
TARIFFS = CONFIG.get("tariffs", {})
ENGINE = create_engine(
    f"postgresql://{DB_CONF['user']}:{DB_CONF['password']}@{DB_CONF['host']}:{DB_CONF['port']}/{DB_CONF['name']}",
    pool_size=5, max_overflow=10, pool_timeout=30, pool_pre_ping=True
)
RESAMPLE_INTERVAL = "10min"
INTERVAL_MS = {"1min": 1*60*1000, "5min": 5*60*1000, "10min": 10*60*1000}.get(RESAMPLE_INTERVAL, 10*60*1000)
cache = TTLCache(maxsize=100, ttl=300)  # 5-minute cache

register_page(__name__, path="/devices", name="Devices")

def fetch_data(device_id, date_selected, view):
    cache_key = f"{device_id}_{view}_{date_selected}"
    if cache_key in cache:
        logger.debug(f"Cache hit for {cache_key}")
        return cache[cache_key]
    
    device = CONFIG.get("devices", {}).get(device_id, {})
    supports = device.get("supports", [])
    if view == "Detailed":
        start = datetime.combine(date_selected, datetime.min.time()).astimezone()
        end = start + pd.Timedelta(days=1)
    elif view == "Daily":
        start = datetime.combine(date_selected, datetime.min.time()).astimezone()
        end = start + pd.Timedelta(days=1)
    elif view == "Weekly":
        start = datetime.combine(date_selected, datetime.min.time()).astimezone()
        end = start + pd.Timedelta(days=7*4)
    elif view == "Monthly":
        start = datetime.combine(date_selected.replace(month=1, day=1), datetime.min.time()).astimezone()
        end = start + pd.Timedelta(days=365)
    else:  # Yearly
        start = datetime.combine(date_selected.replace(month=1, day=1), datetime.min.time()).astimezone()
        end = start + pd.Timedelta(days=365*5)
    
    select_cols = ["timestamp"]
    if "import_kwh" in supports:
        select_cols.append("total_import_kwh")
    if "export_kwh" in supports:
        select_cols.append("total_export_kwh")
    if "gas_m3" in supports:
        select_cols.append("total_gas_m3")
    
    query = text(f"""
        SELECT {', '.join(select_cols)}
        FROM readings
        WHERE timestamp >= :start AND timestamp < :end
        AND device_id = :device_id
        AND (total_import_kwh > 0 OR total_export_kwh > 0 OR total_gas_m3 > 0)
        ORDER BY timestamp
    """)
    with ENGINE.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"start": start, "end": end, "device_id": device_id})
    
    if df.empty:
        logger.debug(f"No data for {device_id} in {view} view")
        df = pd.DataFrame(columns=["timestamp", "total_import_kwh", "total_export_kwh", "total_gas_m3", "import_kwh", "export_kwh", "gas_m3", "import_cost", "export_cost", "gas_cost"])
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("Europe/Brussels")
        df.set_index("timestamp", inplace=True)
        
        # Calculate diffs for incremental values
        if "total_import_kwh" in df:
            df["import_kwh"] = df["total_import_kwh"].diff().clip(lower=0).fillna(0)
        else:
            df["import_kwh"] = 0
        
        if "total_export_kwh" in df:
            df["export_kwh"] = -df["total_export_kwh"].diff().clip(lower=0).fillna(0)
        else:
            df["export_kwh"] = 0
        
        if "total_gas_m3" in df and df["total_gas_m3"].notnull().any():
            df["gas_m3"] = df["total_gas_m3"].diff().clip(lower=0).fillna(0)
        else:
            df["gas_m3"] = 0
        
        # Resample to appropriate intervals
        if view == "Detailed":
            df = df.resample(RESAMPLE_INTERVAL).sum().reset_index()  # 10-minute intervals (144 bars per day)
        elif view == "Daily":
            df = df.resample('D').sum().reset_index()  # Daily sums
        elif view == "Weekly":
            df = df.resample('W').sum().reset_index()  # Weekly sums
        elif view == "Monthly":
            df = df.resample('M').sum().reset_index()  # Monthly sums
        elif view == "Yearly":
            df = df.resample('Y').sum().reset_index()  # Yearly sums
        
        # Calculate costs after resampling
        df["import_cost"] = df["import_kwh"] * TARIFFS.get("import_eur_per_kwh", 0.40)
        df["export_cost"] = df["export_kwh"] * TARIFFS.get("export_eur_per_kwh", 0.04)
        df["gas_cost"] = df["gas_m3"] * TARIFFS.get("gas_eur_per_m3", 0.80)
        
        # Ensure non-empty DataFrame
        if df.empty:
            logger.debug(f"Resampled DataFrame empty for {device_id} in {view} view")
            df = pd.DataFrame(columns=["timestamp", "import_kwh", "export_kwh", "gas_m3", "import_cost", "export_cost", "gas_cost"])
    
    logger.debug(f"Data for {device_id} in {view} view: {len(df)} rows")
    cache[cache_key] = df
    return df

layout = html.Div(
    style={"padding": "20px", "max-width": "1200px", "margin": "auto"},
    children=[
        html.H2("Device Energy Usage"),
        dcc.Dropdown(
            id="device-selector",
            options=[{"label": device.get("name", key), "value": key} for key, device in CONFIG.get("devices", {}).items() if device.get("active", False)],
            value="main_meter",
            style={"width": "200px", "margin": "10px 0"}
        ),
        dcc.DatePickerSingle(id="date-picker", date=date.today(), style={"margin": "10px 0"}),
        dcc.Dropdown(
            id="view-selector",
            options=[
                {"label": "Detailed", "value": "Detailed"},
                {"label": "Daily", "value": "Daily"},
                {"label": "Weekly", "value": "Weekly"},
                {"label": "Monthly", "value": "Monthly"},
                {"label": "Yearly", "value": "Yearly"}
            ],
            value="Detailed",
            style={"width": "200px", "margin": "10px 0"}
        ),
        dcc.Interval(id="interval-component", interval=INTERVAL_MS, n_intervals=0),
        dcc.Loading([
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(150px, 1fr))", "gap": "10px", "margin": "10px 0"},
                children=[
                    html.Div([html.P("Total Import"), html.H4(id="card-import")]),
                    html.Div([html.P("Total Export"), html.H4(id="card-export")]),
                    html.Div([html.P("Total Gas"), html.H4(id="card-gas")])
                ]
            ),
            html.Div(id="electricity-graph"),
            html.Div(id="gas-graph"),
            html.Div(id="cost-graph")
        ])
    ]
)

@callback(
    [
        Output("electricity-graph", "children"),
        Output("gas-graph", "children"),
        Output("cost-graph", "children"),
        Output("card-import", "children"),
        Output("card-export", "children"),
        Output("card-gas", "children")
    ],
    [
        Input("device-selector", "value"),
        Input("date-picker", "date"),
        Input("view-selector", "value"),
        Input("interval-component", "n_intervals")
    ]
)
def update_graphs_and_cards(device_id, date_selected, view, n_intervals):
    df = fetch_data(device_id, pd.to_datetime(date_selected).date(), view)
    device = CONFIG.get("devices", {}).get(device_id, {})
    if df.empty or df[["import_kwh", "export_kwh", "gas_m3"]].sum().sum() == 0:
        logger.debug(f"No valid data for {device_id} in {view} view")
        no_data = html.P(f"No data available for {device.get('name', device_id)} in this period")
        return no_data, no_data, no_data, "—", "—", "—"
    
    x_title = f"Time ({RESAMPLE_INTERVAL})" if view == "Detailed" else view
    x_format = "%H:%M" if view == "Detailed" else "%Y-%m-%d" if view == "Daily" else "%Y-W%W" if view == "Weekly" else "%Y-%m" if view == "Monthly" else "%Y"
    
    # Electricity graph
    if view == "Detailed":
        fig_elec = go.Figure()
        fig_elec.add_trace(go.Bar(
            x=df["timestamp"], y=df["import_kwh"],
            name="Import (kWh)", marker_color=device.get("color", "purple"),
            width=600000,  # 10 minutes in milliseconds
            marker_line_width=1, marker_line_color='white'
        ))
        fig_elec.add_trace(go.Bar(
            x=df["timestamp"], y=df["export_kwh"],
            name="Export (kWh)", marker_color=device.get("export_color", "green"),
            width=600000,
            marker_line_width=1, marker_line_color='white'
        ))
        fig_elec.update_layout(
            barmode="relative", autosize=True, showlegend=False,
            xaxis_title=x_title, yaxis_title="Consumption (kWh)",
            title="Electricity Usage", xaxis_tickformat=x_format,
            bargap=0
        )
    else:
        fig_elec = px.bar(
            df, x="timestamp", y=["import_kwh", "export_kwh"], barmode="relative",
            labels={"timestamp": x_title, "value": "Consumption (kWh)"},
            title="Electricity Usage",
            color_discrete_map={
                "import_kwh": device.get("color", "purple"),
                "export_kwh": device.get("export_color", "green")
            }
        )
        fig_elec.update_traces(
            marker_line_width=0, marker_line_color='rgba(0,0,0,0)', 
            opacity=1.0, width=0.2
        )
        fig_elec.update_layout(autosize=True, showlegend=False, xaxis_tickformat=x_format, bargap=0)
    
    # Gas graph (conditional)
    gas_graph = html.P("Gas data not supported") if "gas_m3" not in device.get("supports", []) else dcc.Graph(
        figure=(
            go.Figure(
                go.Bar(
                    x=df["timestamp"], y=df["gas_m3"],
                    name="Gas (m³)", marker_color=device.get("gas_color", "red"),
                    width=600000 if view == "Detailed" else None,
                    marker_line_width=1 if view == "Detailed" else 0,
                    marker_line_color='white' if view == "Detailed" else 'rgba(0,0,0,0)'
                )
            ).update_layout(
                barmode="relative", autosize=True, showlegend=False,
                xaxis_title=x_title, yaxis_title="Consumption (m³)",
                title="Gas Usage", xaxis_tickformat=x_format, bargap=0
            ).update_traces(
                opacity=1.0
            ) if view == "Detailed" else
            px.bar(
                df, x="timestamp", y="gas_m3",
                labels={"timestamp": x_title, "value": "Consumption (m³)"},
                title="Gas Usage",
                color_discrete_map={"gas_m3": device.get("gas_color", "red")}
            ).update_traces(
                marker_line_width=0, marker_line_color='rgba(0,0,0,0)', 
                opacity=1.0, width=0.2
            ).update_layout(autosize=True, showlegend=False, xaxis_tickformat=x_format, bargap=0)
        )
    )
    
    # Cost graph
    if view == "Detailed":
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=df["timestamp"], y=df["import_cost"],
            name="Import Cost (€)", marker_color=device.get("color", "purple"),
            width=600000,
            marker_line_width=1, marker_line_color='white'
        ))
        fig_cost.add_trace(go.Bar(
            x=df["timestamp"], y=df["export_cost"],
            name="Export Cost (€)", marker_color=device.get("export_color", "green"),
            width=600000,
            marker_line_width=1, marker_line_color='white'
        ))
        if "gas_m3" in device.get("supports", []):
            fig_cost.add_trace(go.Bar(
                x=df["timestamp"], y=df["gas_cost"],
                name="Gas Cost (€)", marker_color=device.get("gas_color", "red"),
                width=600000,
                marker_line_width=1, marker_line_color='white'
            ))
        fig_cost.update_layout(
            barmode="relative", autosize=True, showlegend=False,
            xaxis_title=x_title, yaxis_title="Cost (€)",
            title="Energy Cost", xaxis_tickformat=x_format, bargap=0
        )
    else:
        fig_cost = px.bar(
            df, x="timestamp", y=["import_cost", "export_cost"] + (["gas_cost"] if "gas_m3" in device.get("supports", []) else []),
            barmode="relative",
            labels={"timestamp": x_title, "value": "Cost (€)"},
            title="Energy Cost",
            color_discrete_map={
                "import_cost": device.get("color", "purple"),
                "export_cost": device.get("export_color", "green"),
                "gas_cost": device.get("gas_color", "red")
            }
        )
        fig_cost.update_traces(
            marker_line_width=0, marker_line_color='rgba(0,0,0,0)', 
            opacity=1.0, width=0.2
        )
        fig_cost.update_layout(autosize=True, showlegend=False, xaxis_tickformat=x_format, bargap=0)
    
    # Summary cards
    total_import = df["import_kwh"].sum() if "import_kwh" in df else 0
    total_export = abs(df["export_kwh"].sum()) if "export_kwh" in df else 0
    total_gas = df["gas_m3"].sum() if "gas_m3" in df else 0
    import_text = f"{total_import:,.3f} kWh, €{df['import_cost'].sum():,.2f}"
    export_text = f"{total_export:,.3f} kWh, €{abs(df['export_cost'].sum()):,.2f}"
    gas_text = f"{total_gas:,.3f} m³, €{df['gas_cost'].sum():,.2f}" if "gas_m3" in device.get("supports", []) else "—"
    
    return (
        dcc.Graph(figure=fig_elec),
        gas_graph,
        dcc.Graph(figure=fig_cost),
        import_text,
        export_text,
        gas_text
    )