#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Campaign Schedule Populator at $(date)"
cronlock python -m src.scripts.campaign_schedule_populator
echo "Finished Campaign Schedule Populator at $(date)"