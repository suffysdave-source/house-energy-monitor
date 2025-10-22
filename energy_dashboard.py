# energy_dashboard.py
#
# Description:
# This script runs a Flask web server to display energy data from the p1_meter_data
# table in the PostgreSQL database (consumption_db). It shows a table and Plotly charts
# for the latest records or past 100 records from a user-selected date/time, with
# columns for timestamp, total_power_import_kwh, total_power_export_kwh, active_power_w,
# and total_gas_m3. Timestamps are formatted without microseconds. It uses the same
# config.json as p1_meter_reader.py for database connection details. Errors and startup
# URLs are logged to energy_dashboard_log.txt and console. Designed for a Chromebook
# Linux container (Crostini) using a Python virtual environment. Serves a favicon to
# suppress 404 errors.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version with Flask-based webpage displaying
#                           p1_meter_data table in a simple HTML table.
# Version 1.1 (2025-10-22): Added favicon.ico serving to suppress 404 errors in logs.
# Version 1.2 (2025-10-22): Added startup URL logging and Plotly charts for
#                           visualizing energy data over time.
# Version 1.3 (2025-10-22): Added date picker and time entry field to show past 100
#                           records from a selected date/time (defaulting to current),
#                           and formatted timestamps to exclude microseconds.

import json
import logging
import psycopg2
from flask import Flask, render_template_string, send_from_directory, request
import plotly
import plotly.graph_objs as go
import json
from datetime import datetime

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('energy_dashboard_log.txt'),
        logging.StreamHandler()
    ]
)

# Load configuration from config.json
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except Exception as e:
    logging.error(f"Error loading config.json: {e}")
    exit(1)

# Extract database configuration
DB_HOST = config['database']['host']
DB_NAME = config['database']['name']
DB_USER = config['database']['user']
DB_PASSWORD = config['database']['password']

# Initialize Flask app with static folder
app = Flask(__name__, static_folder='static')

# HTML template for the webpage
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Energy Dashboard</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { text-align: center; }
        h2 { margin-top: 30px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f5f5f5; }
        .plotly-chart { margin-bottom: 30px; }
        .filter-form { margin: 20px 0; text-align: center; }
        .filter-form label { margin-right: 10px; }
        .filter-form input { padding: 5px; margin-right: 10px; }
        .filter-form button { padding: 5px 10px; }
    </style>
</head>
<body>
    <h1>Energy Consumption Dashboard</h1>
    <div class="filter-form">
        <form action="/filter" method="get">
            <label for="selected_date">Date:</label>
            <input type="date" id="selected_date" name="selected_date" value="{{ current_date }}">
            <label for="selected_time">Time:</label>
            <input type="time" id="selected_time" name="selected_time" value="{{ current_time }}">
            <button type="submit">Filter</button>
        </form>
    </div>
    <h2>Power Import (kWh)</h2>
    <div id="power_import_chart" class="plotly-chart"></div>
    <h2>Power Export (kWh)</h2>
    <div id="power_export_chart" class="plotly-chart"></div>
    <h2>Active Power (W)</h2>
    <div id="active_power_chart" class="plotly-chart"></div>
    <h2>Gas Consumption (m³)</h2>
    <div id="gas_chart" class="plotly-chart"></div>
    <h2>Data Table</h2>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Total Power Import (kWh)</th>
            <th>Total Power Export (kWh)</th>
            <th>Active Power (W)</th>
            <th>Total Gas (m³)</th>
        </tr>
        {% for row in data %}
        <tr>
            <td>{{ row.timestamp }}</td>
            <td>{{ row.total_power_import_kwh }}</td>
            <td>{{ row.total_power_export_kwh }}</td>
            <td>{{ row.active_power_w }}</td>
            <td>{{ row.total_gas_m3 }}</td>
        </tr>
        {% endfor %}
    </table>
    <script>
        // Power Import Chart
        var power_import_trace = {
            x: {{ power_import_x | tojson }},
            y: {{ power_import_y | tojson }},
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Power Import (kWh)'
        };
        var power_import_layout = {
            title: '',
            xaxis: { title: 'Timestamp' },
            yaxis: { title: 'kWh' }
        };
        Plotly.newPlot('power_import_chart', [power_import_trace], power_import_layout);

        // Power Export Chart
        var power_export_trace = {
            x: {{ power_export_x | tojson }},
            y: {{ power_export_y | tojson }},
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Power Export (kWh)'
        };
        var power_export_layout = {
            title: '',
            xaxis: { title: 'Timestamp' },
            yaxis: { title: 'kWh' }
        };
        Plotly.newPlot('power_export_chart', [power_export_trace], power_export_layout);

        // Active Power Chart
        var active_power_trace = {
            x: {{ active_power_x | tojson }},
            y: {{ active_power_y | tojson }},
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Active Power (W)'
        };
        var active_power_layout = {
            title: '',
            xaxis: { title: 'Timestamp' },
            yaxis: { title: 'W' }
        };
        Plotly.newPlot('active_power_chart', [active_power_trace], active_power_layout);

        // Gas Chart
        var gas_trace = {
            x: {{ gas_x | tojson }},
            y: {{ gas_y | tojson }},
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Gas (m³)'
        };
        var gas_layout = {
            title: '',
            xaxis: { title: 'Timestamp' },
            yaxis: { title: 'm³' }
        };
        Plotly.newPlot('gas_chart', [gas_trace], gas_layout);
    </script>
</body>
</html>
"""

# Route for favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

# Route for the homepage (default to current time)
@app.route('/')
def display_data():
    # Default to current date and time
    current_time = datetime.now()
    return fetch_data(current_time)

# Route for filtered data
@app.route('/filter')
def filter_data():
    try:
        # Get date and time from query parameters
        selected_date = request.args.get('selected_date')
        selected_time = request.args.get('selected_time')
        
        # Combine date and time, default to current if not provided
        if selected_date and selected_time:
            selected_datetime = datetime.strptime(f"{selected_date} {selected_time}", '%Y-%m-%d %H:%M')
        else:
            selected_datetime = datetime.now()
        
        return fetch_data(selected_datetime)
    except ValueError as e:
        logging.error(f"Error parsing date/time: {e}")
        return "Invalid date or time format. Use YYYY-MM-DD and HH:MM.", 400

# Function to fetch and render data
def fetch_data(selected_datetime):
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Fetch the 100 records before the selected date/time, formatted without microseconds
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
        
        # Render the HTML template
        return render_template_string(
            HTML_TEMPLATE,
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
        return "Error loading data. Check energy_dashboard_log.txt for details.", 500

# Log startup URLs
logging.info("Starting Flask server...")
logging.info("Webpage available at: http://localhost:5000")
logging.info("Also accessible at: http://100.115.92.200:5000 (within Crostini network)")

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)