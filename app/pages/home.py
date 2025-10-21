# File: home.py
# Purpose: Defines the Home page for the House Energy Monitor Streamlit app.
#          Displays real-time power usage, daily metrics, and a 24-hour usage plot.
# Version: 1.1.0

import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import datetime
import os
import sys

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

st.set_page_config(page_title="Home - House Energy Monitor", page_icon=":house:", layout="wide")

def home_page(config):
    """
    Renders the Home page with power usage metrics and a 24-hour plot.
    Args:
        config (dict): Configuration loaded from config.json.
    """
    st.title("House Energy Monitor Dashboard")
    st.markdown("Welcome to the House Energy Monitor! Monitor real-time power usage, view device status, and analyze historical data.")
    
    # Load configuration
    try:
        db_path = config.get('database_path', 'energy.db')
    except Exception as e:
        st.error(f"Failed to read config: {str(e)}")
        return
    
    # Connect to SQLite database
    try:
        conn = sqlite3.connect(db_path)
        query = "SELECT timestamp, power_usage FROM energy_data WHERE timestamp >= datetime('now', '-1 day')"
        df = pd.read_sql_query(query, conn, parse_dates=['timestamp'])
        conn.close()
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        return
    except Exception as e:
        st.error(f"Unexpected error loading data: {str(e)}")
        return
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        current_usage = df['power_usage'].iloc[-1] if not df.empty else 0
        st.metric("Current Power Usage", f"{current_usage:.2f} W", delta=None)
    with col2:
        avg_usage = df['power_usage'].mean() if not df.empty else 0
        st.metric("Daily Average", f"{avg_usage:.2f} W", delta=None)
    with col3:
        peak_usage = df['power_usage'].max() if not df.empty else 0
        st.metric("Peak Usage (24h)", f"{peak_usage:.2f} W", delta=None)
    
    # Plot power usage over time
    if not df.empty:
        try:
            fig = px.line(df, x='timestamp', y='power_usage', title="Power Usage (Last 24 Hours)")
            fig.update_layout(xaxis_title="Time", yaxis_title="Power (W)")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error rendering plot: {str(e)}")
    else:
        st.warning("No data available for the last 24 hours.")