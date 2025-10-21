# File: config.py
# Purpose: Loads configuration from config.json for the House Energy Monitor app.
#          Provides a get_config() function with error handling for Streamlit compatibility.
# Version: 1.1.0

import json
import os
import streamlit as st

def get_config():
    """
    Load configuration from config.json with error handling for Streamlit.
    Returns a dict from config.json or an empty dict if loading fails.
    """
    try:
        # Construct path to config.json (relative to utils/config.py)
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
        # Normalize path to handle any OS-specific issues
        config_path = os.path.normpath(config_path)
        
        if not os.path.exists(config_path):
            st.error(f"Configuration file not found at: {config_path}")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON in config.json: {str(e)}")
        return {}
    except Exception as e:
        st.error(f"Failed to load config.json: {str(e)}")
        return {}