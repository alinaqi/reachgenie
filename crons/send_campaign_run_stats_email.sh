#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Send Campaign Run Stats Email at $(date)"
cronlock python -m src.scripts.send_campaign_run_stats_email
echo "Finished Send Campaign Run Stats Email at $(date)"