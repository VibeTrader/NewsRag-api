#!/bin/bash

# Azure App Service Startup Script for NewsRag API
echo "Starting NewsRag API..."

# Activate virtual environment if it exists
if [ -d "antenv" ]; then
    source antenv/bin/activate
    echo "Virtual environment activated"
fi

# Set default port if not provided
export PORT=${PORT:-8000}
echo "Starting on port: $PORT"

# Start the FastAPI application
python -m uvicorn api:app --host 0.0.0.0 --port $PORT --workers 1