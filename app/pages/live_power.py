# File: live_power.py
# Purpose: Live Power page for the House Energy Monitor app.
#          Displays real-time power usage with auto-refresh and live chart.
# Version: 1.0.0

import streamlit as st
import pandas as pd
import plotly.express as px
import time
import sys
import os

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

def live_power_page(config):
    """
    Renders the Live Power page with real-time updates.
    Args:
        config (dict): Configuration loaded from config.json.
    """
    st.title("Live Power Monitoring")
    st.markdown("Real-time power usage with automatic refresh.")
    
    # Load configuration
    try:
        refresh_interval = config.get('refresh_interval', 5)  # seconds
    except Exception as e:
        st.error(f"Failed to read config: {str(e)}")
        refresh_interval = 5
    
    # Placeholder for live data (replace with actual sensor/API call)
    @st.cache_data(ttl=refresh_interval)
    def get_live_data():
        # Simulate live data
        now = pd.Timestamp.now()
        data = pd.DataFrame({
            'timestamp': [now - pd.Timedelta(seconds=i) for i in range(60, 0, -5)],
            'power_usage': [100 + 50 * pd.sin(i / 10) for i in range(12)]  # Simulated sine wave
        })
        return data
    
    df = get_live_data()
    
    # Live metric
    st.metric("Current Power", f"{df['power_usage'].iloc[-1]:.1f} W")
    
    # Live chart
    fig = px.line(df, x='timestamp', y='power_usage', title="Live Power Usage (Last 5 Minutes)")
    fig.update_layout(xaxis_title="Time", yaxis_title="Power (W)")
    st.plotly_chart(fig, use_container_width=True)
    
    # Auto-refresh button
    if st.button("Refresh Now"):
        st.cache_data.clear()
        st.rerun()
    
    st.info(f"Auto-refresh every {refresh_interval} seconds.")