#!/bin/bash

set -e

#Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "[*] Creating virtual environment..."
  python3 -m venv venv
fi

#Activate
source venv/bin/activate

#Install dependencies
echo "[*] Installing dependencies..."
pip install -r requirements.txt -q

#Open browser after a short delay (let the server start first)
(sleep 2 && xdg-open http://localhost:8000) &

#Run
echo "[*] Starting SCRPR at http://localhost:8000"
uvicorn main:app --reload --port 8000