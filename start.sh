#!/bin/bash
# TR YouTube 24H Live Studio — Linux / VPS start
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; echo "Created .env — EDIT TR_LIVE_ADMIN_TOKEN in .env, then run again."; exit 1; fi
.venv/bin/python backend.py
