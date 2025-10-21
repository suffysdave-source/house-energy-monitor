# File: configuration.py
# Purpose: Configuration page for the House Energy Monitor app.
#          Allows editing and saving settings like database path and log intervals via a form.
# Version: 1.0.0

import streamlit as st
import json
import os
import sys

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

def configuration_page(config):
    """
    Renders the Configuration page with a form to edit and save config.json.
    Args:
        config (dict): Current configuration loaded from config.json.
    """
    st.title("Configuration Settings")
    st.markdown("Edit application settings and save changes to config.json.")
    
    # Load current config with error handling
    try:
        current_config = get_config()
    except Exception as e:
        st.error(f"Failed to load current config: {str(e)}")
        current_config = {}
    
    # Form for editing config
    with st.form("config_form"):
        db_path = st.text_input("Database Path", value=current_config.get('database_path', 'energy.db'))
        log_file = st.text_input("Log File Path", value=current_config.get('log_file', 'logs/energy.log'))
        refresh_interval = st.number_input("Refresh Interval (seconds)", value=current_config.get('refresh_interval', 60), min_value=1)
        submitted = st.form_submit_button("Save Changes")
    
    if submitted:
        new_config = {
            'database_path': db_path,
            'log_file': log_file,
            'refresh_interval': refresh_interval
        }
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.json')
            with open(config_path, 'w') as f:
                json.dump(new_config, f, indent=4)
            st.success("Configuration saved successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save config: {str(e)}")
    
    # Display current config
    st.subheader("Current Configuration")
    st.json(current_config)