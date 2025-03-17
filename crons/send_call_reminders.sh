#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Sending Call Reminders at $(date)"
cronlock python -m src.scripts.send_call_reminders
echo "Finished Sending Call Reminders at $(date)"