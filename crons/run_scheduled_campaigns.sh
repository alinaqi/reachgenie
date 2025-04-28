#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting to Run Scheduled Campaigns at $(date)"
cronlock python -m src.scripts.run_scheduled_campaigns
echo "Finished Running Scheduled Campaigns at $(date)"