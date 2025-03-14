#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Sending Reminders at $(date)"
cronlock python -m src.scripts.send_reminders
echo "Finished Sending Reminders at $(date)"