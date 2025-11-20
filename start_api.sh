#!/bin/bash
# Script to start the API server with virtual environment

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Start the API server
python api_server.py
