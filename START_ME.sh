#!/bin/bash
echo "Starting SSH Automation Server..."
echo

# Load environment variables from .env file
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Continuing without .env file..."
    echo
    SERVER_PORT=5000
else
    echo "✓ .env file found"
    # Load environment variables from .env file
    export $(grep -v '^#' .env | xargs)
fi

# Set default port if SERVER_PORT is not defined
if [ -z "$SERVER_PORT" ]; then
    SERVER_PORT=5000
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
    echo "Virtual environment 'venv' not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment!"
        echo "Please ensure Python 3 is installed and try again."
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Virtual environment created"
    
    # Activate the newly created virtual environment immediately
    echo "Activating new virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to activate virtual environment!"
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Virtual environment activated"
    
    # Install dependencies for the newly created virtual environment
    echo
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    INSTALL_RESULT=$?
    if [ $INSTALL_RESULT -ne 0 ]; then
        echo "ERROR: Dependencies installation failed!"
        echo "Please check your internet connection and try again."
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ All dependencies installed successfully"
else
    echo "✓ Virtual environment found"
    
    # Activate existing virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to activate virtual environment!"
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Virtual environment activated"
    
    # Install/update dependencies for existing virtual environment
    echo
    echo "Updating dependencies..."
    pip install -r requirements.txt
    INSTALL_RESULT=$?
    if [ $INSTALL_RESULT -ne 0 ]; then
        echo "ERROR: Dependencies installation failed!"
        echo "Please check your internet connection and try again."
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Dependencies updated successfully"
fi

# Verify critical dependencies are ready before starting Flask
echo
echo "Verifying dependencies..."

# Ensure we're using virtual environment's Python for verification
VENV_PYTHON="venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment Python executable not found!"
    read -p "Press any key to continue..." -n1 -s
    exit 1
fi

# Test critical packages one by one with detailed feedback
CHECK_SUCCESS=true

echo "Checking Flask..."
$VENV_PYTHON -c "import flask; print('✓ Flask available')" || CHECK_SUCCESS=false

echo "Checking Paramiko..."
$VENV_PYTHON -c "import paramiko; print('✓ Paramiko available')" || CHECK_SUCCESS=false

echo "Checking Pandas..."
$VENV_PYTHON -c "import pandas; print('✓ Pandas available')" || CHECK_SUCCESS=false

echo "Checking openpyxl..."
$VENV_PYTHON -c "import openpyxl; print('✓ OpenPyXL available')" || CHECK_SUCCESS=false

if [ "$CHECK_SUCCESS" = false ]; then
    echo "ERROR: Some critical dependencies are missing - terminating"
    read -p "Press any key to continue..." -n1 -s
    exit 1
fi

echo "✓ All critical dependencies verified"

# Run the Flask application
echo
echo "Starting Flask application..."

# Use the absolute path to the virtual environment's Python to ensure we're using the right environment
VENV_PYTHON="venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment Python executable not found at $VENV_PYTHON!"
    exit 1
fi

echo "Using virtual environment Python at: $VENV_PYTHON"

# Run the Flask app using the virtual environment's Python
$VENV_PYTHON main.py &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 3

# Open browser to 127.0.0.1 with dynamic port
echo "Opening browser at http://127.0.0.1:$SERVER_PORT..."
open http://127.0.0.1:$SERVER_PORT

echo
echo "SSH Automation Server is now running!"
echo "You can access it at: http://127.0.0.1:$SERVER_PORT"
echo
echo "Press any key to keep this window open (this won't stop the server)..."
read -n1 -s

# Optional: Keep the server running and cleanup on exit
trap "echo 'Stopping server...'; kill $SERVER_PID 2>/dev/null; exit" INT
wait $SERVER_PID
