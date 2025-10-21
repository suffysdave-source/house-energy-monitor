from __future__ import annotations
from dash import html, dcc, register_page
from utils.config import load_config

register_page(__name__, path="/user-guide", name="User Guide")

# Load config for dynamic content
config = load_config()
log_file = config.get("logging", {}).get("log_file", "/home/dave/projects/house/logs/energy.log")

# User Guide content in Markdown
chapters = [
    {
        "id": "log-levels",
        "title": "Log Levels",
        "content": """
### Log Levels

The House Energy Monitor uses a logging system to record events, errors, and diagnostic information. The logging level, set via the Configuration page (`http://localhost:8050/configuration`), determines which messages are written to `{log_file}` and displayed in the Log View page (`http://localhost:8050/log-view`). Below are the available log levels, ordered by increasing severity:

- **DEBUG (Lowest, Severity 10)**:
  - **Purpose**: Provides detailed diagnostic information for troubleshooting.
  - **Examples**: 
    - Confirmation of device upserts to the database (e.g., `"Upserted device main_meter"`).
    - Logger initialization details (e.g., `"Initialized file handler for {log_file}"`).
  - **When to Use**: Enable `DEBUG` when investigating issues, such as device connection failures (e.g., `energy_socket_1` timeouts) or database errors. It is verbose and should be used temporarily to avoid filling the log file.
  - **Output Example** (in JSON format, as `"structured": true` in `config.json`):
    ```json
    {{"time": "2025-10-20 13:00:00", "level": "DEBUG", "message": "Upserted device main_meter", "device_id": "main_meter", "error": ""}}
    ```

- **INFO (Low, Severity 20)**:
  - **Purpose**: Confirms normal operation of the application.
  - **Examples**:
    - Logger startup (e.g., `"Starting logger: interval=60s, once=True, level=INFO"`).
    - Completion of a polling cycle (e.g., `"Single cycle complete. Exiting."`).
  - **When to Use**: Use `INFO` for general monitoring to track key events without excessive detail. Less verbose than `DEBUG`.
  - **Output Example**:
    ```json
    {{"time": "2025-10-20 13:00:00", "level": "INFO", "message": "Starting logger: interval=60s, once=True, level=INFO", "device_id": "", "error": ""}}
    ```

- **WARNING (Medium, Severity 30)**:
  - **Purpose**: Indicates potential issues that do not stop the application but may require attention.
  - **Examples**:
    - Failed polling attempts for devices (e.g., `"[Energy Socket 1] Attempt 1/3 failed: HTTPConnectionPool..."`).
  - **When to Use**: Default setting, ideal for capturing recoverable issues like device timeouts (e.g., `energy_socket_1` WiFi disconnections) without cluttering the log.
  - **Output Example**:
    ```json
    {{"time": "2025-10-20 13:00:00", "level": "WARNING", "message": "[Energy Socket 1] Attempt 1/3 failed: HTTPConnectionPool(host='192.168.0.241', port=80): Read timed out. (read timeout=5) (URL: http://192.168.0.241:80/api/v1/data)", "device_id": "energy_socket_1", "error": "HTTPConnectionPool..."}}
    ```

- **ERROR (High, Severity 40)**:
  - **Purpose**: Indicates serious issues that prevent parts of the application from functioning, requiring immediate attention.
  - **Examples**:
    - Failure after all polling retries (e.g., `"[Energy Socket 1] Failed after 3 attempts..."`).
    - Database connection or query failures (e.g., `"Failed to insert reading for main_meter: ..."`).
  - **When to Use**: Use `ERROR` for minimal logging, capturing only critical failures. Suitable for production to reduce log size.
  - **Output Example**:
    ```json
    {{"time": "2025-10-20 13:00:00", "level": "ERROR", "message": "[Energy Socket 1] Failed after 3 attempts (URL: http://192.168.0.241:80/api/v1/data)", "device_id": "energy_socket_1", "error": "All retries failed"}}
    ```

**How It Works**:
- The log level is set in the Configuration page and stored in `/home/dave/projects/house/config/config.json` under `"logging.log_level"`.
- Only messages at or above the set level are logged. For example, setting `"log_level": "WARNING"` includes `WARNING` and `ERROR` messages but excludes `DEBUG` and `INFO`.
- Changes to the log level take effect within 60 seconds (the polling interval) without restarting the application, thanks to dynamic configuration reloading in `logger.py`.
- Logs are written to `{log_file}` in JSON format (as `"structured": true`) and displayed in the Log View page, with the newest entries at the top and long messages truncated with tooltips for full text.

![Log View Screenshot](/assets/log_view.png)
        """.format(log_file=log_file)
    },
    {
        "id": "database-setup",
        "title": "Database Setup",
        "content": """
### Database Setup

The House Energy Monitor uses a PostgreSQL database (`house_energy_db`) to store energy readings and device metadata. The database is configured via the Configuration page (`http://localhost:8050/configuration`) and stored in `/home/dave/projects/house/config/config.json` under the `"database"` section.

- **Database Configuration**:
  - **Host**: The server address (default: `localhost`).
  - **Port**: The server port (default: `5432`).
  - **Name**: The database name (default: `house_energy_db`).
  - **User**: The database user (default: `dave`).
  - **Password**: The database password (default: `energy123`).

- **Tables**:
  - **readings**: Stores energy readings with columns:
    - `device_id`: Identifier for the device (e.g., `main_meter`, `kwh_meter`, `energy_socket_1`).
    - `timestamp`: When the reading was recorded.
    - `total_import_kwh`: Imported energy in kWh.
    - `total_export_kwh`: Exported energy in kWh.
    - `total_gas_m3`: Gas usage in cubic meters (only for `main_meter`).
  - **devices**: Stores device metadata with columns:
    - `device_id`: Unique device identifier.
    - `name`, `ip`, `port`, `api_path`, `supports`, `active`, `updated_at`: Device details and status.

- **Accessing the Database**:
  - Connect using `psql`:
    ```bash
    psql -h localhost -p 5432 -U dave -d house_energy_db
    ```
    Enter password: `energy123`.
  - View tables:
    ```bash
    \\dt
    ```
  - Query readings:
    ```bash
    SELECT * FROM readings ORDER BY timestamp DESC LIMIT 20;
    ```

- **Viewing Data**:
  - The Database View page (`http://localhost:8050/database-view`) allows you to select a table (e.g., `readings`, `devices`) and view the last 20 entries. Use the dropdown to switch tables and the Refresh button to update data.

- **Setup Instructions**:
  - Ensure PostgreSQL is installed and running:
    ```bash
    sudo systemctl start postgresql
    sudo systemctl status postgresql
    ```
  - Create the database if it doesn’t exist:
    ```bash
    createdb -h localhost -p 5432 -U dave house_energy_db
    ```
  - Create tables using a SQL script (e.g., `create_tables.sql`) if not already set up:
    ```sql
    CREATE TABLE devices (
        device_id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(100),
        ip VARCHAR(15),
        port INTEGER,
        api_path VARCHAR(100),
        supports TEXT[],
        active BOOLEAN,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE readings (
        id SERIAL PRIMARY KEY,
        device_id VARCHAR(50) REFERENCES devices(device_id),
        timestamp TIMESTAMP DEFAULT NOW(),
        total_import_kwh DOUBLE PRECISION,
        total_export_kwh DOUBLE PRECISION,
        total_gas_m3 DOUBLE PRECISION
    );
    ```

![Database View Screenshot](/assets/database_view.png)
        """
    },
    {
        "id": "cost-calculations",
        "title": "Cost Calculations",
        "content": """
### Cost Calculations

The House Energy Monitor calculates energy costs based on tariffs defined in `/home/dave/projects/house/config/config.json` under the `"tariffs"` section. These costs are displayed on pages like Main Energy Meter (`http://localhost:8050/main-energy-meter`), kWh Meter (`http://localhost:8050/kwh-meter`), and Energy Socket 1 (`http://localhost:8050/energy-socket-1`).

- **Tariff Configuration**:
  - **Import (€/kWh)**: Cost per kWh of imported electricity (default: `0.3745`).
  - **Export (€/kWh)**: Revenue per kWh of exported electricity (default: `0.031824`).
  - **Gas (€/m³)**: Cost per cubic meter of gas (default: `0.84077`).
  - Set via the Configuration page (`http://localhost:8050/configuration`).

- **Cost Formula**:
  For each device, the cost over a time period is calculated as:
  ```
  Cost (€) = (total_import_kwh * import_eur_per_kwh) - (total_export_kwh * export_eur_per_kwh) + (total_gas_m3 * gas_eur_per_m3)
  ```
  - `total_import_kwh`, `total_export_kwh`, `total_gas_m3`: From the `readings` table for the selected time period.
  - Example (for `main_meter`):
    - If `total_import_kwh = 10`, `total_export_kwh = 5`, `total_gas_m3 = 2`:
    - Cost = `(10 * 0.3745) - (5 * 0.031824) + (2 * 0.84077) = 3.745 - 0.15912 + 1.68154 = 5.26742 €`.

- **Display**:
  - The Main Energy Meter, kWh Meter, and Energy Socket 1 pages show cost graphs in the Detailed view (using configurable intervals, e.g., 10 minutes) and Daily/Weekly/Monthly/Yearly overviews.
  - Costs are computed using data from the `readings` table, aggregated over the selected time period.

![Main Energy Meter Screenshot](/assets/main_energy_meter.png)
        """
    },
    {
        "id": "device-polling",
        "title": "Device Polling",
        "content": """
### Device Polling

The House Energy Monitor polls devices (`main_meter`, `kwh_meter`, `energy_socket_1`) to collect energy readings, which are stored in the `readings` table and logged to `{log_file}`. Polling is managed by `/home/dave/projects/house/scripts/logger.py`.

- **Polling Configuration**:
  - **Interval (seconds)**: Frequency of polling (default: `60`, set in `config.json` under `"polling.interval_seconds"`).
  - **Devices**: Configured in `config.json` under `"devices"`, with fields:
    - `name`, `ip`, `port`, `api_path`, `supports` (e.g., `["import_kwh", "export_kwh", "gas_m3"]`), `active`, `color`.
    - Example:
      ```json
      "main_meter": {{
          "name": "Main Energy Meter",
          "ip": "192.168.0.240",
          "port": 80,
          "api_path": "/api/v1",
          "supports": ["import_kwh", "export_kwh", "gas_m3"],
          "active": true,
          "color": "#FFA500"
      }}
      ```

- **How It Works**:
  - `logger.py` sends HTTP GET requests to each device’s API (e.g., `http://192.168.0.240:80/api/v1/data`).
  - Readings (`total_import_kwh`, `total_export_kwh`, `total_gas_m3`) are stored in the `readings` table.
  - Failures (e.g., `energy_socket_1` timeouts) are logged as `WARNING` (per attempt) or `ERROR` (after all retries).
  - Polling interval is controlled via the Configuration page.

- **Viewing Data**:
  - Live Power page (`http://localhost:8050/live-power`) shows real-time power usage.
  - Database View page (`http://localhost:8050/database-view`) displays historical readings.
  - Log View page (`http://localhost:8050/log-view`) shows polling errors (e.g., `energy_socket_1` timeouts).

![Live Power Screenshot](/assets/live_power.png)
        """.format(log_file=log_file)
    },
    {
        "id": "ui-navigation",
        "title": "UI Navigation",
        "content": """
### UI Navigation

The House Energy Monitor provides a web interface with multiple pages, accessible via the navigation bar at the top of each page. Below is an overview of each page:

- **Home (`http://localhost:8050/`)**:
  - Displays a welcome message and overview of the application.
  - Use as a starting point to navigate other pages.

- **Main Energy Meter (`http://localhost:8050/main-energy-meter`)**:
  - Shows energy usage for the `main_meter` device with graphs for electricity (import/export in kWh), gas (m³), and costs (€).
  - Supports Detailed view (configurable intervals) and Daily/Weekly/Monthly/Yearly overviews.
  - ![Screenshot](/assets/main_energy_meter.png)

- **kWh Meter (`http://localhost:8050/kwh-meter`)**:
  - Displays energy usage for the `kwh_meter` device, similar to Main Energy Meter but without gas (not supported).
  - ![Screenshot](/assets/kwh_meter.png)

- **Energy Socket 1 (`http://localhost:8050/energy-socket-1`)**:
  - Shows energy usage for the `energy_socket_1` device, similar to kWh Meter.
  - ![Screenshot](/assets/energy_socket_1.png)

- **Live Power (`http://localhost:8050/live-power`)**:
  - Displays real-time power usage (Watts) for all active devices, with device-specific colors from `config.json`.
  - Includes a Last Updated timestamp and logs failures.
  - ![Screenshot](/assets/live_power.png)

- **Configuration (`http://localhost:8050/configuration`)**:
  - Allows editing `config.json` settings (database, devices, polling, logging, tariffs).
  - Features tabs, input validation, and a reset button.
  - ![Screenshot](/assets/configuration.png)

- **Database View (`http://localhost:8050/database-view`)**:
  - Displays the last 20 entries from selected tables (`readings`, `devices`) with a dropdown and refresh button.
  - ![Screenshot](/assets/database_view.png)

- **Log View (`http://localhost:8050/log-view`)**:
  - Shows the last 100 entries from `{log_file}`, newest first, with truncated messages and tooltips.
  - Includes a refresh button.
  - ![Screenshot](/assets/log_view.png)

- **User Guide (`http://localhost:8050/user-guide`)**:
  - This page, providing documentation on the application’s features.

![Home Screenshot](/assets/home.png)
        """.format(log_file=log_file)
    },
    {
        "id": "troubleshooting",
        "title": "Troubleshooting",
        "content": """
### Troubleshooting

This section provides guidance on diagnosing and resolving common issues in the House Energy Monitor.

- **Device Connection Issues (e.g., `energy_socket_1` timeouts)**:
  - **Symptoms**: Log entries like:
    ```json
    {{"time": "2025-10-20 13:00:00", "level": "WARNING", "message": "[Energy Socket 1] Attempt 1/3 failed: HTTPConnectionPool...", "device_id": "energy_socket_1", "error": "HTTPConnectionPool..."}}
    ```
  - **Steps**:
    1. Check device connectivity:
       ```bash
       ping 192.168.0.241
       curl -m 5 http://192.168.0.241:80/api/v1/data
       ```
    2. Verify device IP and port in `config.json` via the Configuration page.
    3. Set `log_level` to `DEBUG` in the Configuration page to log additional details.
    4. Check the Log View page for detailed error messages.

- **Database Connection Issues**:
  - **Symptoms**: Log entries like:
    ```json
    {{"time": "2025-10-20 13:00:00", "level": "ERROR", "message": "Database connection failed: ...", "device_id": "", "error": "..."}}
    ```
  - **Steps**:
    1. Ensure PostgreSQL is running:
       ```bash
       sudo systemctl status postgresql
       sudo systemctl start postgresql
       ```
    2. Connect using `psql`:
       ```bash
       psql -h localhost -p 5432 -U dave -d house_energy_db
       ```
    3. Verify `config.json` database settings.
    4. Set `log_level` to `DEBUG` for more details.

- **Log File Issues**:
  - **Symptoms**: No logs in `{log_file}` or errors in the Log View page.
  - **Steps**:
    1. Check permissions:
       ```bash
       ls -l {log_file}
       chmod u+rw {log_file}
       ls -ld /home/dave/projects/house/logs/
       chmod u+rwx /home/dave/projects/house/logs/
       ```
    2. Verify `config.json` logging settings.
    3. Run `logger.py` with `--once`:
       ```bash
       cd /home/dave/projects/house/scripts
       source ../venv/bin/activate
       python logger.py --once
       ```

- **General Debugging**:
  - Set `log_level` to `DEBUG` in the Configuration page.
  - Monitor logs in the Log View page or `{log_file}`.
  - Check terminal output when running `app.py` or `logger.py`.

![Configuration Screenshot](/assets/configuration.png)
        """.format(log_file=log_file)
    }
]

# Layout
layout = html.Div(
    style={"padding": "20px", "max-width": "800px", "margin": "auto"},
    children=[
        html.H2("User Guide", style={"text-align": "center"}),
        html.P("This guide explains the functionality of the House Energy Monitor application.", style={"text-align": "center"}),
        html.H3("Table of Contents"),
        html.Ul([
            html.Li(dcc.Link(chapter["title"], href=f"#chapter-{chapter['id']}", style={"textDecoration": "none"}))
            for chapter in chapters
        ], style={"marginBottom": "20px"}),
        html.Div([
            html.Details([
                html.Summary(chapter["title"], style={"fontWeight": "bold"}),
                dcc.Markdown(chapter["content"], id=f"chapter-{chapter['id']}")
            ], style={"marginBottom": "10px"})
            for chapter in chapters
        ])
    ]
)