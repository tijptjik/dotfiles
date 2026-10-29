#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash -n setup.sh
bash -n scripts/validate.sh
python3 -B -m unittest discover -s tests -v
python3 ../scripts/check-task-templates.py
