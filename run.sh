#!/bin/bash
# AI Bug Investigation System - startup script
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt --break-system-packages -q 2>/dev/null || pip install -r requirements.txt -q
cd backend
echo "Starting server at http://localhost:8000  (Ctrl+C to stop)"
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
