# p1_meter_reader.py
#
# Description:
# This script reads data from a HomeWizard P1-meter via its API over WiFi and stores
# a subset of parameters (total_power_import_kwh, total_power_export_kwh, active_power_w,
# total_gas_m3) in a PostgreSQL database at regular intervals. It uses a configuration
# file (config.json) for API URL, polling interval, and database connection details.
# Errors and key status messages are logged to a file (p1_meter_log.txt) and console.
# Designed for a Chromebook Linux container (Crostini) using a Python virtual environment.
# Includes robust polling with retries, timeouts, response validation, database
# reconnection, graceful shutdown, duplicate prevention, and a PostgreSQL service check.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version with direct database connection and fixed parameters.
# Version 1.1 (2025-10-22): Added config.json support for IP, API URL, polling interval,
#                           parameters to log, and DB details. Dynamic table creation.
# Version 1.2 (2025-10-22): Enhanced polling with retries, timeouts, response validation,
#                           database reconnection, graceful shutdown, duplicate prevention,
#                           and improved logging.
# Version 1.3 (2025-10-22): Limited logged parameters to total_power_import_kwh,
#                           total_power_export_kwh, active_power_w, and total_gas_m3.
# Version 1.4 (2025-10-22): Added table schema validation to ensure only specified
#                           parameters are logged, with option to drop and recreate table.
# Version 1.5 (2025-10-22): Added PostgreSQL service status check and start attempt using
#                           'service' command, with logging and error handling.
# Version 1.6 (2025-10-22): Replaced 'service' with 'systemctl' for PostgreSQL service
#                           check/start to support Crostini, with fallback to manual start.
# Version 1.7 (2025-10-22): Suppressed "Data inserted successfully" log message to reduce
#                           console output, retaining other logs.

import requests
import psycopg2
import json
import time
import logging
import signal
import sys
import subprocess
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('p1_meter_log.txt'),
        logging.StreamHandler()
    ]
)

# Function to check and start PostgreSQL service
def ensure_postgresql_service(max_attempts=3, delay=5):
    for attempt in range(max_attempts):
        try:
            # Check service status
            result = subprocess.run(
                ['systemctl', 'is-active', 'postgresql'],
                capture_output=True, text=True, check=False
            )
            if result.stdout.strip() == 'active':
                logging.info("PostgreSQL service is running.")
                return True
            else:
                logging.warning(f"PostgreSQL service is not running. Attempting to start (attempt {attempt + 1}/{max_attempts})...")
                # Try to start the service
                result = subprocess.run(
                    ['sudo', 'systemctl', 'start', 'postgresql'],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    logging.info("PostgreSQL service started successfully.")
                    return True
                else:
                    logging.error(f"Failed to start PostgreSQL service: {result.stderr}")
        except subprocess.SubprocessError as e:
            logging.error(f"Error checking/starting PostgreSQL service: {e}")
        
        if attempt < max_attempts - 1:
            time.sleep(delay)
    
    logging.error("Failed to start PostgreSQL service after maximum attempts. Please run 'sudo systemctl start postgresql' manually and try again.")
    return False

# Load configuration from config.json
try:
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
except Exception as e:
    logging.error(f"Error loading config.json: {e}")
    sys.exit(1)

# Extract configuration
API_URL = config['p1_meter']['api_url']
INTERVAL_SECONDS = config['polling_interval_seconds']
DB_HOST = config['database']['host']
DB_NAME = config['database']['name']
DB_USER = config['database']['user']
DB_PASSWORD = config['database']['password']

# Define parameters to log
PARAMETERS_TO_LOG = [
    'total_power_import_kwh',
    'total_power_export_kwh',
    'active_power_w',
    'total_gas_m3'
]

# Map API parameter types to PostgreSQL types
PARAM_TYPE_MAP = {
    'total_power_import_kwh': 'NUMERIC',
    'total_power_export_kwh': 'NUMERIC',
    'active_power_w': 'NUMERIC',
    'total_gas_m3': 'NUMERIC'
}

# Set up HTTP session with retries
session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

# Database connection (global for signal handling)
conn = None

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    logging.info("Shutting down gracefully...")
    if conn is not None and not conn.closed:
        conn.close()
        logging.info("Database connection closed.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Function to connect to the database with retry
def connect_db(max_attempts=3, delay=5):
    attempts = 0
    while attempts < max_attempts:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logging.info("Successfully connected to database.")
            return conn
        except Exception as e:
            attempts += 1
            logging.error(f"Database connection attempt {attempts}/{max_attempts} failed: {e}")
            if attempts < max_attempts:
                time.sleep(delay)
    logging.error("Failed to connect to database after maximum attempts.")
    return None

# Function to validate and recreate table if schema is incorrect
def ensure_table(conn):
    try:
        cur = conn.cursor()
        # Check existing table schema
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'p1_meter_data';
        """)
        existing_columns = {row[0] for row in cur.fetchall()}
        expected_columns = {'id', 'timestamp'} | set(PARAMETERS_TO_LOG)
        
        if existing_columns != expected_columns:
            logging.info("Table schema incorrect, dropping and recreating p1_meter_data.")
            cur.execute("DROP TABLE IF EXISTS p1_meter_data;")
            conn.commit()
            
            # Create new table
            columns = [
                'id SERIAL PRIMARY KEY',
                'timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'total_power_import_kwh NUMERIC',
                'total_power_export_kwh NUMERIC',
                'active_power_w NUMERIC',
                'total_gas_m3 NUMERIC',
                'UNIQUE (timestamp)'
            ]
            create_table_sql = f"CREATE TABLE p1_meter_data ({', '.join(columns)});"
            cur.execute(create_table_sql)
            conn.commit()
            logging.info("Database table created with correct schema.")
        else:
            logging.info("Database table schema verified.")
        cur.close()
    except Exception as e:
        logging.error(f"Error ensuring table schema: {e}")
        conn.rollback()

# Function to validate API response
def validate_data(data):
    for param in PARAMETERS_TO_LOG:
        if param not in data or data[param] is None:
            logging.warning(f"Missing or null parameter '{param}' in API response.")
            return False
    return True

# Function to insert data into the database
def insert_data(conn, data):
    try:
        cur = conn.cursor()
        columns = ['timestamp'] + PARAMETERS_TO_LOG
        placeholders = ['%s'] * len(columns)
        values = [datetime.now()] + [data.get(param) for param in PARAMETERS_TO_LOG]
        insert_sql = f"INSERT INTO p1_meter_data ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        cur.execute(insert_sql, values)
        conn.commit()
        cur.close()
    except psycopg2.IntegrityError as e:
        logging.warning(f"Skipping duplicate data insertion: {e}")
        conn.rollback()
    except Exception as e:
        logging.error(f"Error inserting data: {e}")
        conn.rollback()

# Main loop to read data periodically
def main():
    # Check and start PostgreSQL service
    if not ensure_postgresql_service():
        sys.exit(1)

    global conn
    conn = connect_db()
    if conn is None:
        logging.error("Exiting due to database connection failure.")
        sys.exit(1)

    ensure_table(conn)

    while True:
        try:
            # Check database connection
            if conn.closed:
                logging.warning("Database connection lost. Attempting to reconnect...")
                conn = connect_db()
                if conn is None:
                    logging.error("Failed to reconnect to database. Exiting.")
                    sys.exit(1)

            # Fetch data from P1-meter with timeout
            response = session.get(API_URL, timeout=(3, 5))
            response.raise_for_status()
            data = response.json()

            # Validate data
            if validate_data(data):
                insert_data(conn, data)
            else:
                logging.warning("Skipping data insertion due to invalid API response.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data from P1-meter: {e}")
        except ValueError as e:
            logging.error(f"Error parsing JSON: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()