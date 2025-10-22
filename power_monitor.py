# power_monitor.py
#
# Description:
# This script runs a Flask web server to display a real-time scatter graph of the
# active_power_w parameter from the HomeWizard P1-meter API, showing power import
# (positive, purple) and export (negative, green) as dots with thin light grey
# interconnecting lines. A zero power line is displayed. The x-axis shows only start
# and end timestamps (HH:MM:SS) of the observation window. The graph updates smoothly
# via AJAX, adding new points on the right and shifting older points left, with a
# configurable observation window and polling frequency from config.json. Errors are
# logged to power_monitor_log.txt only for unsuccessful API calls. Designed for a
# Chromebook Linux container (Crostini) using a Python virtual environment. Serves a
# favicon to suppress 404 errors.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version with real-time Plotly graph for
#                           active_power_w, configurable via config.json, with
#                           user input for observation window and polling frequency.
# Version 1.1 (2025-10-22): Improved JavaScript for reliable graph updates, added
#                           console logging for debugging, ensured data rendering.
# Version 1.2 (2025-10-22): Changed to bar graph, removed line connections, used
#                           colored bars for power level, set bar width to polling
#                           frequency, and added zero power line.
# Version 1.3 (2025-10-22): Fixed bar width to match polling frequency in milliseconds,
#                           corrected data retention with millisecond timestamps.
# Version 1.4 (2025-10-22): Implemented dynamic bar widths (observation_window / number_of_points),
#                           added shift logic for full window, improved debug logging.
# Version 1.5 (2025-10-22): Reverted to scatter plot with colored dots (purple for import,
#                           green for export) and thin light grey lines, keeping zero line.
# Version 1.6 (2025-10-22): Simplified x-axis to show only start and end timestamps
#                           of the observation window.

import json
import logging
import requests
from flask import Flask, render_template_string, send_from_directory, request
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('power_monitor_log.txt'),
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

# Extract configuration
API_URL = config['p1_meter']['api_url']
OBSERVATION_WINDOW = config.get('power_monitor', {}).get('observation_window_seconds', 300)
POLLING_FREQUENCY = max(config.get('power_monitor', {}).get('polling_frequency_seconds', 2), 2)

# Initialize Flask app with static folder
app = Flask(__name__, static_folder='static')

# In-memory storage for power data
power_data = []

# Set up HTTP session with retries
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

# HTML template for the webpage
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Power Monitor</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { text-align: center; }
        .plotly-chart { margin-bottom: 30px; }
        .config-form { margin: 20px 0; text-align: center; }
        .config-form label { margin-right: 10px; }
        .config-form input { padding: 5px; margin-right: 10px; }
        .config-form button { padding: 5px 10px; }
    </style>
</head>
<body>
    <h1>Power Monitor</h1>
    <div class="config-form">
        <form id="config-form">
            <label for="window">Observation Window (seconds):</label>
            <input type="number" id="window" name="window" value="{{ observation_window }}" min="10">
            <label for="frequency">Polling Frequency (seconds):</label>
            <input type="number" id="frequency" name="frequency" value="{{ polling_frequency }}" min="2" step="0.1">
            <button type="submit">Apply</button>
        </form>
    </div>
    <div id="power_chart" class="plotly-chart"></div>
    <script>
        let powerData = [];
        let observationWindow = {{ observation_window }};
        let pollingFrequency = {{ polling_frequency }};
        const maxPoints = Math.ceil(observationWindow / pollingFrequency);

        // Initialize Plotly chart
        Plotly.newPlot('power_chart', [{
            x: [],
            y: [],
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#D3D3D3', width: 1 },
            marker: { size: 8, color: [] }
        }], {
            title: 'Active Power (W)',
            xaxis: { title: 'Time (HH:MM:SS)', tickvals: [], ticktext: [] },
            yaxis: { title: 'Power (W)' },
            shapes: [{
                type: 'line',
                x0: 0,
                x1: 1,
                xref: 'paper',
                y0: 0,
                y1: 0,
                line: { color: 'black', width: 1, dash: 'dash' }
            }]
        });

        // Function to fetch and update data
        function updateChart() {
            $.getJSON('/api/power', function(data) {
                console.log('Received:', data, 'Length:', powerData.length, 'Max:', maxPoints);
                if (data.timestamp && data.active_power_w !== null && !data.error) {
                    const msTimestamp = Date.now();
                    powerData.push({
                        msTimestamp: msTimestamp,
                        timestamp: data.timestamp,
                        value: data.active_power_w,
                        color: data.active_power_w >= 0 ? '#800080' : '#008000' // Purple for import, green for export
                    });

                    // Remove old data points
                    const cutoff = Date.now() - observationWindow * 1000;
                    powerData = powerData.filter(point => point.msTimestamp >= cutoff);

                    // Limit to max points
                    if (powerData.length > maxPoints) {
                        powerData.shift();
                    }

                    // Prepare data for Plotly
                    const x = powerData.map(point => point.timestamp);
                    const y = powerData.map(point => point.value);
                    const colors = powerData.map(point => point.color);

                    // Calculate start and end timestamps for x-axis labels
                    const endTime = new Date();
                    const startTime = new Date(endTime.getTime() - observationWindow * 1000);
                    const tickvals = [x[0], x[x.length - 1] || x[0]];
                    const ticktext = [
                        startTime.toISOString().slice(11, 19), // HH:MM:SS
                        endTime.toISOString().slice(11, 19)
                    ];

                    // Redraw chart
                    Plotly.newPlot('power_chart', [{
                        x: x,
                        y: y,
                        type: 'scatter',
                        mode: 'lines+markers',
                        line: { color: '#D3D3D3', width: 1 },
                        marker: { size: 8, color: colors }
                    }], {
                        title: 'Active Power (W)',
                        xaxis: { title: 'Time (HH:MM:SS)', tickvals: tickvals, ticktext: ticktext },
                        yaxis: { title: 'Power (W)', range: [Math.min(...y, 0) - 50, Math.max(...y, 0) + 50] },
                        shapes: [{
                            type: 'line',
                            x0: 0,
                            x1: 1,
                            xref: 'paper',
                            y0: 0,
                            y1: 0,
                            line: { color: 'black', width: 1, dash: 'dash' }
                        }]
                    });
                } else {
                    console.log('Invalid data:', data);
                }
            }).fail(function(jqXHR, textStatus, errorThrown) {
                console.log('Error fetching power data:', textStatus, errorThrown);
            });

            setTimeout(updateChart, pollingFrequency * 1000);
        }

        // Start updates
        updateChart();

        // Handle form submission
        $('#config-form').submit(function(e) {
            e.preventDefault();
            observationWindow = parseInt($('#window').val()) || observationWindow;
            pollingFrequency = Math.max(parseFloat($('#frequency').val()) || pollingFrequency, 2);
            powerData = []; // Clear data to reset window
            Plotly.newPlot('power_chart', [{
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#D3D3D3', width: 1 },
                marker: { size: 8, color: [] }
            }], {
                title: 'Active Power (W)',
                xaxis: { title: 'Time (HH:MM:SS)', tickvals: [], ticktext: [] },
                yaxis: { title: 'Power (W)' },
                shapes: [{
                    type: 'line',
                    x0: 0,
                    x1: 1,
                    xref: 'paper',
                    y0: 0,
                    y1: 0,
                    line: { color: 'black', width: 1, dash: 'dash' }
                }]
            });
            updateChart();
        });
    </script>
</body>
</html>
"""

# Route for favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

# Route for the homepage
@app.route('/')
def display_power_monitor():
    return render_template_string(
        HTML_TEMPLATE,
        observation_window=OBSERVATION_WINDOW,
        polling_frequency=POLLING_FREQUENCY
    )

# API endpoint for power data
@app.route('/api/power')
def get_power_data():
    try:
        response = session.get(API_URL, timeout=(3, 5))
        response.raise_for_status()
        data = response.json()
        active_power_w = data.get('active_power_w')
        if active_power_w is None:
            logging.error("Missing active_power_w in API response")
            return {'error': 'Missing active_power_w'}, 500
        return {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'active_power_w': float(active_power_w)  # Ensure numeric value
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from P1-meter: {e}")
        return {'error': str(e)}, 500
    except ValueError as e:
        logging.error(f"Error parsing JSON: {e}")
        return {'error': str(e)}, 500

# Log startup URLs
logging.info("Starting Flask server...")
logging.info("Power Monitor available at: http://localhost:5001")
logging.info("Also accessible at: http://100.115.92.200:5001 (within Crostini network)")

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)