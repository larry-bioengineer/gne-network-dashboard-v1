#!/bin/bash
echo "Starting SSH Automation Server..."
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Continuing without .env file..."
    echo
else
    echo "✓ .env file found"
fi

# Check if config_file/data.xlsx exists
if [ ! -f "config_file/data.xlsx" ]; then
    echo "ERROR: config_file/data.xlsx not found!"
    echo "Please ensure data.xlsx exists in the config_file directory."
    read -p "Press any key to continue..." -n1 -s
    exit 1
else
    echo "✓ config_file/data.xlsx found"
fi

# Check if venv directory exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment 'venv' not found!"
    echo "Please create a virtual environment first."
    read -p "Press any key to continue..." -n1 -s
    exit 1
else
    echo "✓ Virtual environment found"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment!"
    read -p "Press any key to continue..." -n1 -s
    exit 1
fi
echo "✓ Virtual environment activated"

# Install dependencies if needed
echo
echo "Checking dependencies..."
pip install -r requirements.txt >/dev/null 2>&1

# Run the Flask application
echo
echo "Starting Flask application..."
python main.py &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 3

# Open browser to 127.0.0.1:5000
echo "Opening browser at http://127.0.0.1:5000..."
open http://127.0.0.1:5000

echo
echo "SSH Automation Server is now running!"
echo "You can access it at: http://127.0.0.1:5000"
echo
echo "Press any key to keep this window open (this won't stop the server)..."
read -n1 -s

# Optional: Keep the server running and cleanup on exit
trap "echo 'Stopping server...'; kill $SERVER_PID 2>/dev/null; exit" INT
wait $SERVER_PID
