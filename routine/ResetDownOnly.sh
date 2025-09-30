#!/bin/bash
echo "Starting Reset Down Only Script..."
echo

# Load environment variables from .env file
if [ ! -f "../.env" ]; then
    echo "WARNING: .env file not found!"
    echo "Continuing without .env file..."
    echo
else
    echo "✓ .env file found"
    # Load environment variables from .env file
    export $(grep -v '^#' ../.env | xargs)
fi

# Check if config_file/data.xlsx exists
if [ ! -f "../config_file/data.xlsx" ]; then
    echo "ERROR: config_file/data.xlsx not found!"
    echo "Please ensure data.xlsx exists in the config_file directory."
    read -p "Press any key to continue..." -n1 -s
    exit 1
else
    echo "✓ config_file/data.xlsx found"
fi

# Check if venv directory exists
if [ ! -d "../venv" ]; then
    echo "Virtual environment 'venv' not found!"
    echo "Creating virtual environment..."
    cd ..
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment!"
        echo "Please ensure Python 3 is installed and try again."
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Virtual environment created"
    cd routine
    
    # Activate the newly created virtual environment immediately
    echo "Activating new virtual environment..."
    source ../venv/bin/activate
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
    pip install -r ../requirements.txt
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
    source ../venv/bin/activate
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to activate virtual environment!"
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Virtual environment activated"
    
    # Install/update dependencies for existing virtual environment
    echo
    echo "Updating dependencies..."
    pip install -r ../requirements.txt
    INSTALL_RESULT=$?
    if [ $INSTALL_RESULT -ne 0 ]; then
        echo "ERROR: Dependencies installation failed!"
        echo "Please check your internet connection and try again."
        read -p "Press any key to continue..." -n1 -s
        exit 1
    fi
    echo "✓ Dependencies updated successfully"
fi

# Verify critical dependencies are ready before running the script
echo
echo "Verifying dependencies..."

# Ensure we're using virtual environment's Python for verification
VENV_PYTHON="../venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment Python executable not found!"
    read -p "Press any key to continue..." -n1 -s
    exit 1
fi

# Test critical packages one by one with detailed feedback
CHECK_SUCCESS=true

echo "Checking Pandas..."
$VENV_PYTHON -c "import pandas; print('✓ Pandas available')" || CHECK_SUCCESS=false

echo "Checking Paramiko..."
$VENV_PYTHON -c "import paramiko; print('✓ Paramiko available')" || CHECK_SUCCESS=false

echo "Checking openpyxl..."
$VENV_PYTHON -c "import openpyxl; print('✓ OpenPyXL available')" || CHECK_SUCCESS=false

echo "Checking python-dotenv..."
$VENV_PYTHON -c "import dotenv; print('✓ python-dotenv available')" || CHECK_SUCCESS=false

if [ "$CHECK_SUCCESS" = false ]; then
    echo "ERROR: Some critical dependencies are missing - terminating"
    read -p "Press any key to continue..." -n1 -s
    exit 1
fi

echo "✓ All critical dependencies verified"

# Run the ResetDownOnly.py script
echo
echo "Starting Reset Down Only Script..."
echo

# Use the virtual environment's Python to run the reset script
$VENV_PYTHON ResetDownOnly.py
SCRIPT_RESULT=$?

# Check the exit code and display appropriate message
if [ $SCRIPT_RESULT -eq 0 ]; then
    echo
    echo "✓ Reset Down Only Script completed successfully!"
elif [ $SCRIPT_RESULT -eq 1 ]; then
    echo
    echo "❌ Reset Down Only Script failed with errors!"
elif [ $SCRIPT_RESULT -eq 2 ]; then
    echo
    echo "⚠️ Reset Down Only Script completed with some failures!"
else
    echo
    echo "❌ Reset Down Only Script exited with code $SCRIPT_RESULT"
fi

echo
echo "Press any key to exit..."
read -n1 -s
