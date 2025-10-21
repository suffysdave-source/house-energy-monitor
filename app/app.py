import streamlit as st
from streamlit_option_menu import option_menu
import sys
import os

# Add the utils directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

# Import pages
from pages.home import home_page
from pages.live_power import live_power_page
from pages.device import device_page
from pages.log_view import log_view_page
from pages.database_view import database_view_page
from pages.configuration import configuration_page
from pages.user_guide import user_guide_page
from config import get_config  # From utils/config.py

# Page configuration
st.set_page_config(
    page_title="House Energy Monitor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sidebar .sidebar-content {
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Load configuration with error handling
    try:
        config = get_config()
    except Exception as e:
        st.error(f"Failed to load config: {str(e)}")
        config = {}  # Fallback to empty dict to prevent crashes
        return

    # Sidebar navigation
    with st.sidebar:
        st.title("⚡ Energy Monitor")
        st.markdown("---")
        
        selected = option_menu(
            menu_title=None,
            options=["Home", "Live Power", "Devices", "Logs", "Database", "Config", "Guide"],
            icons=["house", "graph-up", "plug", "file-earmark-text", "database", "gear", "book"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
        )
        st.markdown("---")
        st.info("**Version:** 1.0.0\n**Status:** Monitoring Active")
    
    # Debug output to trace navigation
    st.write(f"Debug: Selected option is '{selected}'")
    
    # Page routing
    if selected == "Home":
        home_page(config)
    elif selected == "Live Power":
        live_power_page(config)
    elif selected == "Devices":
        device_page(config)
    elif selected == "Logs":
        log_view_page(config)
    elif selected == "Database":
        database_view_page(config)
    elif selected == "Config":
        configuration_page(config)
    elif selected == "Guide":
        user_guide_page(config)
    else:
        st.error(f"Unknown page selected: {selected}")

if __name__ == "__main__":
    main()