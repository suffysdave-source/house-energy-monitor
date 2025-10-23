# modules/dashboard.py
#
# Description:
# This module handles the logic for the Energy Dashboard page, fetching data from
# consumption_db and rendering the dashboard.html template with table and charts.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version for modular Energy Dashboard.

import json
import logging
import psycopg2
from flask import render_template
from datetime import datetime

# Load configuration from config.json
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except Exception as e:
    logging.error(f"Error loading config.json: {e}")
    raise

# Extract database configuration
DB_HOST = config['database']['host']
DB_NAME = config['database']['name']
DB_USER = config['database']['user']
DB_PASSWORD = config['database']['password']

def render_dashboard(request):
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Get date and time from query parameters
        selected_date = request.args.get('selected_date')
        selected_time = request.args.get('selected_time')
        if selected_date and selected_time:
            try:
                selected_datetime = datetime.strptime(f"{selected_date} {selected_time}", '%Y-%m-%d %H:%M')
            except ValueError as e:
                logging.error(f"Error parsing date/time: {e}")
                return "Invalid date or time format. Use YYYY-MM-DD and HH:MM.", 400
        else:
            selected_datetime = datetime.now()
        
        # Fetch the 100 records before the selected date/time
        cur.execute("""
            SELECT to_char(timestamp, 'YYYY-MM-DD HH24:MI:SS'),
                   total_power_import_kwh, total_power_export_kwh,
                   active_power_w, total_gas_m3
            FROM p1_meter_data
            WHERE timestamp <= %s
            ORDER BY timestamp DESC
            LIMIT 100;
        """, (selected_datetime,))
        rows = cur.fetchall()
        
        # Convert rows to a list of dictionaries for the table
        data = [
            {
                'timestamp': row[0],
                'total_power_import_kwh': row[1],
                'total_power_export_kwh': row[2],
                'active_power_w': row[3],
                'total_gas_m3': row[4]
            } for row in rows
        ]
        
        # Prepare data for charts
        timestamps = [row[0] for row in rows]
        power_import_y = [row[1] for row in rows]
        power_export_y = [row[2] for row in rows]
        active_power_y = [row[3] for row in rows]
        gas_y = [row[4] for row in rows]
        
        cur.close()
        conn.close()
        
        # Format current date and time for form defaults
        current_date = selected_datetime.strftime('%Y-%m-%d')
        current_time = selected_datetime.strftime('%H:%M')
        
        return render_template(
            'dashboard.html',
            data=data,
            power_import_x=timestamps,
            power_import_y=power_import_y,
            power_export_x=timestamps,
            power_export_y=power_export_y,
            active_power_x=timestamps,
            active_power_y=active_power_y,
            gas_x=timestamps,
            gas_y=gas_y,
            current_date=current_date,
            current_time=current_time
        )
    
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return "Error loading data. Check app_log.txt for details.", 500