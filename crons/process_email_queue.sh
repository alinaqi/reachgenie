#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Processing Email Queue at $(date)"
cronlock python -m src.scripts.process_email_queues
echo "Finished Processing Email Queue at $(date)"