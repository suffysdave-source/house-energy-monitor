# File: database_view.py
# Purpose: Database view page for the House Energy Monitor app.
#          Displays a table of energy data from the SQLite database and allows custom queries.
# Version: 1.0.0

import streamlit as st
import pandas as pd
import sqlite3
import sys
import os

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))
from utils.config import get_config

def database_view_page(config):
    """
    Renders the Database View page with a data table and query input.
    Args:
        config (dict): Configuration loaded from config.json.
    """
    st.title("Database View")
    st.markdown("View and query the energy data stored in the SQLite database.")
    
    # Load configuration
    try:
        db_path = config.get('database_path', 'energy.db')
    except Exception as e:
        st.error(f"Failed to read config: {str(e)}")
        return
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        st.error(f"Database connection failed: {str(e)}")
        return
    
    # Default query
    default_query = "SELECT * FROM energy_data ORDER BY timestamp DESC LIMIT 100"
    query = st.text_area("SQL Query", value=default_query, height=100)
    
    if st.button("Run Query"):
        try:
            df = pd.read_sql_query(query, conn)
            st.dataframe(df, use_container_width=True)
            st.metric("Total Records", len(df))
        except Exception as e:
            st.error(f"Query error: {str(e)}")
    
    conn.close()
    
    # Show schema
    if st.checkbox("Show Table Schema"):
        cursor = sqlite3.connect(db_path).cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            st.subheader(f"Schema for {table[0]}")
            cursor.execute(f"PRAGMA table_info({table[0]})")
            schema = cursor.fetchall()
            st.table(pd.DataFrame(schema, columns=['cid', 'name', 'type', 'notnull', 'default', 'pk']))
        cursor.close()