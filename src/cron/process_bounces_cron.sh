#!/bin/bash

# Script to process email bounces
# Should be run as a cron job, e.g. every 30 minutes

# Change to the project root directory
cd "$(dirname "$0")/../.."

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Set the PYTHONPATH to include the current directory
export PYTHONPATH=$(pwd):$PYTHONPATH

# Run the bounce processing script
echo "Starting bounce processing at $(date)"
python -m src.scripts.process_bounces
echo "Finished bounce processing at $(date)"

# Exit with the script's exit code
exit $? 