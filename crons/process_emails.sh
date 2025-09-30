#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app

echo "Starting Processing Inbox Emails at $(date)"
cronlock python -m src.scripts.process_emails
echo "Finished Processing Inbox Emails at $(date)"