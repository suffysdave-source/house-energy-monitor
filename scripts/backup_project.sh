# backup_project.sh
#
# Description:
# This script creates a zip archive of all files in ~/projects/house, excluding the
# venv directory, and saves it to ~/projects/backup with a filename including the
# current date and time (e.g., backup_20251022_1013.zip). Designed for a Chromebook
# Linux container (Crostini) to back up P1-meter project files.
#
# Version History:
# Version 1.0 (2025-10-22): Initial version to zip ~/projects/house files (excluding
#                           venv) and save to ~/projects/backup with timestamped filename.

#!/bin/bash

# Set source and backup directories
SOURCE_DIR="$HOME/projects/house"
BACKUP_DIR="$HOME/projects/backup"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp for filename (YYYYMMDD_HHMM)
TIMESTAMP=$(date +%Y%m%d_%H%M)

# Set output zip file path
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.zip"

# Check if zip is installed
if ! command -v zip &> /dev/null; then
    echo "Error: zip command not found. Install it with 'sudo apt install zip'"
    exit 1
fi

# Create zip archive, excluding venv directory
echo "Creating backup of $SOURCE_DIR to $BACKUP_FILE..."
if zip -r "$BACKUP_FILE" "$SOURCE_DIR" -x "$SOURCE_DIR/venv/*" > /dev/null; then
    echo "Backup successfully created: $BACKUP_FILE"
else
    echo "Error: Failed to create backup. Check permissions or disk space."
    exit 1
fi

exit 0