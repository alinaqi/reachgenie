#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Processing Call Queue at $(date)"
cronlock python -m src.scripts.process_call_queues
echo "Finished Processing Call Queue at $(date)"