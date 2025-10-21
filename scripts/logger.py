#!/usr/bin/env python3
import os
import sys
import time
import json
import signal
import logging
from logging.handlers import TimedRotatingFileHandler
import argparse
import requests
import psycopg2

# Suppress urllib3 logging
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Adjust Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.config import load_config

# Global state for signal handling
RUNNING = True

def _handle_sigterm(signum, frame):
    global RUNNING
    RUNNING = False

signal.signal(signal.SIGINT, _handle_sigterm)
signal.signal(signal.SIGTERM, _handle_sigterm)

# Logging setup
def setup_logging(config):
    """Configure logging with time-based rotation, no console output."""
    logger = logging.getLogger("house_energy")
    log_level = config.get("log_level", "WARNING").upper()
    logger.setLevel(getattr(logging, log_level, logging.WARNING))
    logger.handlers.clear()

    structured = config.get("structured", False)
    if structured:
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                    "level": record.levelname,
                    "message": record.msg,
                    "device_id": getattr(record, "device_id", ""),
                    "error": getattr(record, "error", "")
                }
                return json.dumps(log_entry)
        fmt = JsonFormatter()
    else:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")

    log_file = config.get("log_file")
    if config.get("enabled", True) and log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            max_bytes = config.get("max_bytes", 5 * 1024 * 1024)
            backup_count = config.get("backup_count", 3)
            time_based = config.get("time_based_rotation", False)
            
            if time_based:
                fh = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=backup_count)
            else:
                fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            logger.info(f"Initialized file handler for {log_file} with level {log_level}", extra={"device_id": "", "error": ""})
        except Exception as e:
            logger.error(f"Failed to initialize file handler for {log_file}: {e}", extra={"device_id": "", "error": str(e)})
            # Fallback to null handler to prevent console output
            logger.addHandler(logging.NullHandler())
    else:
        logger.info("File logging disabled or no log file specified", extra={"device_id": "", "error": ""})
        logger.addHandler(logging.NullHandler())
    return logger

# Database connection
def get_db_conn(db_conf, log):
    """Create a PostgreSQL database connection."""
    try:
        return psycopg2.connect(
            host=db_conf["host"],
            port=db_conf["port"],
            dbname=db_conf["name"],
            user=db_conf["user"],
            password=db_conf["password"],
            connect_timeout=5
        )
    except Exception as e:
        log.error(f"Database connection failed: {e}", extra={"device_id": "", "error": str(e)})
        sys.exit(1)

# Database operations
def upsert_device(cur, device_id, meta, log):
    """Upsert device metadata into the database."""
    try:
        cur.execute(
            """
            INSERT INTO devices (device_id, name, ip, port, api_path, supports, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (device_id) DO UPDATE
            SET name = EXCLUDED.name, ip = EXCLUDED.ip, port = EXCLUDED.port,
                api_path = EXCLUDED.api_path, supports = EXCLUDED.supports,
                active = EXCLUDED.active, updated_at = NOW()
            """,
            (
                device_id,
                meta.get("name"),
                meta.get("ip"),
                meta.get("port", 80),
                meta.get("api_path", "/api/v1"),
                meta.get("supports", []),
                meta.get("active", True)
            )
        )
        log.debug(f"Upserted device {device_id}", extra={"device_id": device_id, "error": ""})
    except Exception as e:
        log.error(f"Failed to upsert device {device_id}: {e}", extra={"device_id": device_id, "error": str(e)})

def insert_reading(cur, device_id, import_kwh, export_kwh, gas_m3, log):
    """Insert a reading into the database, logging only failures."""
    try:
        cur.execute(
            """
            INSERT INTO readings (device_id, timestamp, total_import_kwh, total_export_kwh, total_gas_m3)
            VALUES (%s, NOW(), %s, %s, %s)
            """,
            (device_id, import_kwh, export_kwh, gas_m3)
        )
    except Exception as e:
        log.error(f"Failed to insert reading for {device_id}: {e}", extra={"device_id": device_id, "error": str(e)})

# Device polling
def poll_device(device_id, meta, timeout, retries, log):
    """Poll device API for energy readings."""
    url = f"http://{meta['ip']}:{meta.get('port', 80)}{meta.get('api_path', '/api/v1')}/data"
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            import_kwh = float(data.get("total_power_import_kwh", 0)) if "import_kwh" in meta.get("supports", []) else None
            export_kwh = float(data.get("total_power_export_kwh", 0)) if "export_kwh" in meta.get("supports", []) else None
            gas_m3 = float(data.get("total_gas_m3", 0)) if "gas_m3" in meta.get("supports", []) else None
            return import_kwh, export_kwh, gas_m3
        except Exception as e:
            log.warning(
                f"[{meta.get('name', device_id)}] Attempt {attempt}/{retries} failed: {str(e)} (URL: {url})",
                extra={"device_id": device_id, "error": str(e)}
            )
            time.sleep(1)
    log.error(
        f"[{meta.get('name', device_id)}] Failed after {retries} attempts (URL: {url})",
        extra={"device_id": device_id, "error": "All retries failed"}
    )
    return None, None, None

# Main logic
def main():
    """Main entry point for the House Energy Logger."""
    parser = argparse.ArgumentParser(description="House Energy Logger")
    parser.add_argument("--once", action="store_true", help="Poll devices once and exit")
    args = parser.parse_args()

    config = load_config()
    db_conf = config["database"]
    log_config = config.get("logging", {})
    log = setup_logging(log_config)
    log.info(f"Starting logger: interval={config.get('polling', {}).get('interval_seconds', 60)}s, once={args.once}, level={logging.getLevelName(log.level)}", extra={"device_id": "", "error": ""})

    conn = get_db_conn(db_conf, log)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            for device_id, meta in config.get("devices", {}).items():
                upsert_device(cur, device_id, meta, log)

        while RUNNING:
            tick_start = time.time()
            # Reload config to apply changes dynamically
            config = load_config()
            log_config = config.get("logging", {})
            log = setup_logging(log_config)  # Reinitialize logger with updated config
            devices = config.get("devices", {})
            poll_interval = config.get("polling", {}).get("interval_seconds", 60)

            with conn.cursor() as cur:
                for device_id, meta in devices.items():
                    if not meta.get("active", True):
                        continue
                    import_kwh, export_kwh, gas_m3 = poll_device(device_id, meta, timeout=5, retries=3, log=log)
                    if import_kwh is not None or export_kwh is not None or gas_m3 is not None:
                        insert_reading(cur, device_id, import_kwh, export_kwh, gas_m3, log)

            if args.once:
                log.info("Single cycle complete. Exiting.", extra={"device_id": "", "error": ""})
                break
            time.sleep(max(0, poll_interval - (time.time() - tick_start)))
    except KeyboardInterrupt:
        log.info("Interrupted. Exiting.", extra={"device_id": "", "error": ""})
    finally:
        conn.close()

if __name__ == "__main__":
    main()