#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app
# Run without cronlock since Redis isn't available
python -m src.scripts.process_email_queues 