#!/bin/bash

# 1. Navigate to the project directory
cd "$(dirname "$0")"

# 2. Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment (.venv) not found. Please run installation first."
    exit 1
fi

# 3. Set Python path
export PYTHONPATH=$PYTHONPATH:.

# 4. Launch PartnerOS
echo "🚀 Starting PartnerOS v3.2 — The Third Partner..."
streamlit run src/ui/app.py
