import json
import logging
from flask import Flask, render_template, send_from_directory, request
from modules.home import render_home
from modules.dashboard import render_dashboard
from modules.power import get_power_data, power_monitor

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_log.txt'),
        logging.StreamHandler()
    ]
)

# Initialize Flask app with template and static folders
app = Flask(__name__, template_folder='templates', static_folder='static')

# Route for favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

# Route for homepage
@app.route('/')
def home():
    return render_home()

# Route for Energy Dashboard
@app.route('/dashboard')
def dashboard():
    return render_dashboard(request)

# Route for Power Monitor
@app.route('/power')
def power_monitor_route():
    return power_monitor()

# API endpoint for power data
@app.route('/api/power')
def power_data():
    return get_power_data()

# Log startup URLs
logging.info("Starting Flask server...")
logging.info("Application available at: http://localhost:5000")
logging.info("Also accessible at: http://100.115.92.200:5000 (within Crostini network)")

# Run the Flask app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)