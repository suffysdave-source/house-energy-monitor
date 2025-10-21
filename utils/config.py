# File: config.py
# Description: Utility for loading configuration and database connection with error handling.
# Version: 1.4
# Author: Dave (optimized with Grok)
# Created: 2025-10-19
# Last Modified: 2025-10-21

import os
import json
from sqlalchemy import create_engine
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_config(config_path="/home/dave/projects/house/config/config.json"):
    try:
        config_path = os.path.abspath(config_path)
        logger.debug(f"Loading config from {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Ensure database section exists
        if "database" not in config:
            logger.warning("No 'database' key in config.json, using defaults")
            config["database"] = {
                "host": "localhost",
                "port": 5432,
                "name": "house_energy_db",
                "user": os.getenv("DB_USER", "dave"),
                "password": os.getenv("DB_PASSWORD", "energy123")
            }
        # Override database credentials with environment variables if set
        config["database"]["user"] = os.getenv("DB_USER", config["database"].get("user", "dave"))
        config["database"]["password"] = os.getenv("DB_PASSWORD", config["database"].get("password", "energy123"))
        config["database"]["host"] = config["database"].get("host", "localhost")
        config["database"]["port"] = config["database"].get("port", 5432)
        config["database"]["name"] = config["database"].get("name", "house_energy_db")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}")
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "house_energy_db",
                "user": os.getenv("DB_USER", "dave"),
                "password": os.getenv("DB_PASSWORD", "energy123")
            }
        }
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file at {config_path}")
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "house_energy_db",
                "user": os.getenv("DB_USER", "dave"),
                "password": os.getenv("DB_PASSWORD", "energy123")
            }
        }
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "house_energy_db",
                "user": os.getenv("DB_USER", "dave"),
                "password": os.getenv("DB_PASSWORD", "energy123")
            }
        }

CONFIG = load_config()
ENGINE = create_engine(
    f"postgresql://{CONFIG['database']['user']}:{CONFIG['database']['password']}@{CONFIG['database']['host']}:{CONFIG['database']['port']}/{CONFIG['database']['name']}",
    pool_size=5, max_overflow=10, pool_timeout=30, pool_pre_ping=True
)