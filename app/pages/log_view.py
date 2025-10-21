# File: log_view.py
# Purpose: Log View page for the House Energy Monitor app.
#          Displays recent entries from the energy log file.
# Version: 1.1.0

import streamlit as st
import pandas as pd
import os
import sys

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

def log_view_page(config):
    """
    Renders the Log View page with recent log entries.
    Args:
        config (dict): Configuration loaded from config.json.
    """
    st.title("Log Viewer")
    st.markdown("View recent entries from the energy log file.")
    
    # Load configuration
    try:
        log_file = config.get('log_file', '/home/dave/projects/house/logs/energy.log')
    except Exception as e:
        st.error(f"Failed to read config: {str(e)}")
        return
    
    # Read log file
    try:
        if os.path.exists(log_file):
            df = pd.read_csv(log_file, names=['timestamp', 'event', 'power'], parse_dates=['timestamp'])
            df = df.tail(100)  # Last 100 entries
            st.dataframe(df, use_container_width=True)
            st.metric("Total Log Entries", len(df))
        else:
            st.warning(f"Log file not found: {log_file}")
    except Exception as e:
        st.error(f"Failed to read log file: {str(e)}")
    
    # Filter logs
    level = st.selectbox("Filter by Level", ["All", "INFO", "WARNING", "ERROR"])
    if level != "All":
        filtered_df = df[df['event'].str.contains(level, case=False)]
        st.dataframe(filtered_df)