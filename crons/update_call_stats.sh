#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Updating Call Stats at $(date)"
cronlock python -m src.scripts.update_call_stats
echo "Finished Updating Call Stats at $(date)"
