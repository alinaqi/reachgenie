#!/bin/bash
set -o errexit -o nounset -o pipefail
cd /app
cronlock python -m src.scripts.update_call_stats