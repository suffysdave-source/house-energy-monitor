# modules/power.py
#
# Description:
# This module handles the logic for the Power Monitor page, fetching real-time
# active_power_w data from the P1-meter API and rendering the power.html template.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version for modular Power Monitor.

import json
import logging
import requests
from flask import render_template, jsonify
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load configuration from config.json
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except Exception as e:
    logging.error(f"Error loading config.json: {e}")
    raise

# Extract configuration
API_URL = config['p1_meter']['api_url']
OBSERVATION_WINDOW = config.get('power_monitor', {}).get('observation_window_seconds', 300)
POLLING_FREQUENCY = max(config.get('power_monitor', {}).get('polling_frequency_seconds', 2), 2)

# In-memory storage for power data
power_data = []

# Set up HTTP session with retries
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

def power_monitor():
    return render_template(
        'power.html',
        observation_window=OBSERVATION_WINDOW,
        polling_frequency=POLLING_FREQUENCY
    )

def get_power_data():
    try:
        response = session.get(API_URL, timeout=(3, 5))
        response.raise_for_status()
        data = response.json()
        active_power_w = data.get('active_power_w')
        if active_power_w is None:
            logging.error("Missing active_power_w in API response")
            return jsonify({'error': 'Missing active_power_w'}), 500
        return jsonify({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'active_power_w': float(active_power_w)
        })
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from P1-meter: {e}")
        return jsonify({'error': str(e)}), 500
    except ValueError as e:
        logging.error(f"Error parsing JSON: {e}")
        return jsonify({'error': str(e)}), 500