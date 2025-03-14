#!/bin/bash

# Script to process email bounces
# Should be run as a cron job, e.g. every 30 minutes

# Set the PYTHONPATH to include the current directory
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run the bounce processing script
echo "Starting bounce processing at $(date)"
cronlock python -m src.scripts.process_bounces
echo "Finished bounce processing at $(date)"

# Exit with the script's exit code
exit $? 