# File: device.py
# Purpose: Devices page for the House Energy Monitor app.
#          Displays status and power usage for connected devices.
# Version: 1.0.0

import streamlit as st
import pandas as pd
import sys
import os

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

def device_page(config):
    """
    Renders the Devices page with a table of device statuses.
    Args:
        config (dict): Configuration loaded from config.json.
    """
    st.title("Device Management")
    st.markdown("View and manage connected devices and their power usage.")
    
    # Load configuration
    try:
        devices_config = config.get('devices', [])
    except Exception as e:
        st.error(f"Failed to read device config: {str(e)}")
        devices_config = []
    
    # Sample device data (replace with real data from DB or API)
    device_data = pd.DataFrame({
        'Device': ['Fridge', 'Lights', 'AC Unit', 'Charger'],
        'Status': ['Online', 'Online', 'Offline', 'Online'],
        'Power (W)': [150, 50, 0, 20],
        'Last Update': ['2025-10-21 12:00', '2025-10-21 11:50', '2025-10-21 11:30', '2025-10-21 12:05']
    })
    
    # Display device table
    st.subheader("Device Status")
    st.dataframe(device_data, use_container_width=True)
    
    # Device controls
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Device")
        new_device = st.text_input("Device Name")
        new_power = st.number_input("Expected Power (W)", min_value=0.0)
        if st.button("Add"):
            # Add logic here (e.g., update config or DB)
            st.success(f"Added {new_device}")
    
    with col2:
        st.subheader("Refresh All")
        if st.button("Refresh Status"):
            st.info("Refreshing device statuses...")
            st.rerun()
    
    if not devices_config:
        st.warning("No devices configured. Add some in the Configuration page.")