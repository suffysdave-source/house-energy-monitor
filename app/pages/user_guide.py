# File: user_guide.py
# Purpose: User Guide page for the House Energy Monitor app.
#          Provides documentation and instructions for using the dashboard.
# Version: 1.0.0

import streamlit as st
import sys
import os

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

def user_guide_page(config):
    """
    Renders the User Guide page with markdown documentation.
    Args:
        config (dict): Configuration loaded from config.json (unused here).
    """
    st.title("User Guide")
    st.markdown("""
    ## Welcome to House Energy Monitor
    
    This dashboard helps you track home energy usage in real-time.
    
    ### Getting Started
    1. **Setup**: Ensure your logger script (`scripts/logger.py`) is running to collect data.
    2. **Navigation**: Use the sidebar to switch between pages (Home, Live Power, etc.).
    3. **Configuration**: Edit settings like database path in the Config page.
    
    ### Key Features
    - **Home**: Overview with metrics and 24h chart.
    - **Live Power**: Real-time updates every few seconds.
    - **Devices**: Manage and view device statuses.
    - **Logs**: Review recent log entries.
    - **Database**: Run SQL queries on energy data.
    
    ### Troubleshooting
    - If data is missing, check the logger and database connection.
    - For errors, view the console or logs.
    
    ### Support
    - GitHub Repo: [house-energy-monitor](https://github.com/suffysdave-source/house-energy-monitor)
    - Contact: suffys.dave@gmail.com
    
    For more details, see `documentation/personal_notes.txt`.
    """)
    
    # Load config for version display
    try:
        app_version = config.get('version', '1.0.0')
        st.info(f"App Version: {app_version}")
    except Exception as e:
        st.warning(f"Could not load version: {str(e)}")