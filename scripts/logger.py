# File: logger.py
# Purpose: Logger script for the House Energy Monitor app.
#          Subscribes to MQTT topics to collect energy data and logs to a file.
# Version: 1.0.0

import paho.mqtt.client as mqtt
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import sys
import os

# Ensure utils directory is in the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
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
        log_file = config.get('logging', {}).get('log_file', '/home/dave/projects/house/logs/energy.log')
        log_level = config.get('logging', {}).get('log_level', 'INFO')
        max_bytes = config.get('logging', {}).get('max_bytes', 5242880)
        backup_count = config.get('logging', {}).get('backup_count', 3)
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

def on_connect(client, userdata, flags, rc, properties=None):
    """
    Callback for MQTT connection.
    """
    logger = userdata['logger']
    if rc == 0:
        client.subscribe("energy/main_meter")
        client.subscribe("energy/kwh_meter")
        client.subscribe("energy/energy_socket_1")
        logger.info("Connected to MQTT broker and subscribed to topics")
    else:
        logger.error(f"Failed to connect to MQTT broker with code: {rc}")

def on_message(client, userdata, msg):
    """
    Callback for MQTT message receipt.
    """
    logger = userdata['logger']
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        logger.info(f"Received data from {msg.topic}: {payload}")
        # Add database storage logic here if needed
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
        client = mqtt.Client(userdata={'logger': logger})
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