# File: logger.py
# Purpose: Logger script for the House Energy Monitor app.
#          Subscribes to MQTT topics to collect energy data, logs to a file, and updates PostgreSQL database.
# Version: 1.5.0

import paho.mqtt.client as mqtt
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import psycopg2

from config import get_config

def setup_logger(config):
    """
    Sets up a rotating file logger based on config settings.
    Args:
        config (dict): Configuration from config.json.
    Returns:
        logging.Logger: Configured logger instance.
    """
    try:
        log_file = config.get('logging', {}).get('log_file', 'logs/energy.log')
        log_level = config.get('logging', {}).get('log_level', 'INFO')
        max_bytes = config.get('logging', {}).get('max_bytes', 5242880)
        backup_count = config.get('logging', {}).get('backup_count', 3)
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logger = logging.getLogger('EnergyLogger')
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    except Exception as e:
        print(f"Failed to set up logger: {str(e)}")
        raise

def sync_devices(config, logger):
    """
    Syncs devices from config.json to the PostgreSQL devices table.
    Args:
        config (dict): Configuration from config.json.
        logger: Logger instance for logging.
    """
    try:
        db_config = config.get('database', {})
        db_params = {
            'host': db_config.get('host', 'localhost'),
            'port': db_config.get('port', 5432),
            'database': db_config.get('name', 'house_energy_db'),
            'user': db_config.get('user', 'dave'),
            'password': db_config.get('password', 'energy123')
        }
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        for device_id, details in config.get('devices', {}).items():
            cursor.execute(
                """
                INSERT INTO devices (device_id, name, ip, port, api_path, supports, active, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (device_id) DO UPDATE
                SET name = EXCLUDED.name,
                    ip = EXCLUDED.ip,
                    port = EXCLUDED.port,
                    api_path = EXCLUDED.api_path,
                    supports = EXCLUDED.supports,
                    active = EXCLUDED.active,
                    updated_at = NOW()
                """,
                (
                    device_id,
                    details.get('name', ''),
                    details.get('ip', ''),
                    details.get('port', 80),
                    details.get('api_path', ''),
                    details.get('supports', []),
                    details.get('active', True)
                )
            )
        conn.commit()
        logger.info("Synced devices from config.json to database")
        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        logger.error(f"Failed to sync devices to database: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error syncing devices: {str(e)}")

def on_connect(client, userdata, flags, reason_code, properties=None):
    """
    Callback for MQTT connection.
    """
    logger = userdata['logger']
    if reason_code == 0:
        client.subscribe("energy/main_meter")
        client.subscribe("energy/kwh_meter")
        client.subscribe("energy/energy_socket_1")
        logger.info("Connected to MQTT broker and subscribed to topics")
    else:
        logger.error(f"Failed to connect to MQTT broker with code: {reason_code}")

def on_message(client, userdata, msg):
    """
    Callback for MQTT message receipt.
    Saves data to the readings table in PostgreSQL.
    """
    logger = userdata['logger']
    db_params = userdata['db_params']
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        logger.info(f"Received data from {msg.topic}: {payload}")
        
        # Extract device_id from topic (e.g., energy/main_meter -> main_meter)
        device_id = msg.topic.split('/')[-1]
        
        # Insert into readings table
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO readings (device_id, timestamp, total_import_kwh, total_export_kwh, total_gas_m3)
            VALUES (%s, NOW(), %s, %s, %s)
            """,
            (
                device_id,
                payload.get('total_import_kwh', 0.0),
                payload.get('total_export_kwh', 0.0),
                payload.get('total_gas_m3', 0.0)
            )
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Inserted reading for {device_id} into database")
    except psycopg2.Error as e:
        logger.error(f"Failed to insert reading into database: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing message from {msg.topic}: {str(e)}")

def main():
    """
    Main function to run the MQTT logger.
    """
    try:
        config = get_config()
    except Exception as e:
        print(f"Failed to load config: {str(e)}")
        return
    
    global logger
    logger = setup_logger(config)
    try:
        # Sync devices to database
        sync_devices(config, logger)
        
        # Database connection parameters
        db_config = config.get('database', {})
        db_params = {
            'host': db_config.get('host', 'localhost'),
            'port': db_config.get('port', 5432),
            'database': db_config.get('name', 'house_energy_db'),
            'user': db_config.get('user', 'dave'),
            'password': db_config.get('password', 'energy123')
        }
        
        client = mqtt.Client(protocol=mqtt.MQTTv5, userdata={'logger': logger, 'db_params': db_params})
        client.on_connect = on_connect
        client.on_message = on_message
        mqtt_broker = config.get('mqtt', {}).get('host', 'localhost')
        mqtt_port = config.get('mqtt', {}).get('port', 1883)
        client.connect(mqtt_broker, mqtt_port, 60)
        client.loop_start()
        logger.info("Started MQTT logger")
        while True:
            time.sleep(config.get('polling', {}).get('interval_seconds', 3))
    except Exception as e:
        logger.error(f"Logger error: {str(e)}")
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Logger stopped")

if __name__ == "__main__":
    main()