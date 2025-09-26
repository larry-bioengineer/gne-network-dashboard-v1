@echo off
echo Starting SSH Automation Server...
echo.

:: Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Continuing without .env file...
    echo.
) else (
    echo ✓ .env file found
)

:: Check if config_file/data.xlsx exists
if not exist "config_file\data.xlsx" (
    echo ERROR: config_file/data.xlsx not found!
    echo Please ensure data.xlsx exists in the config_file directory.
    pause
    exit /b 1
) else (
    echo ✓ config_file/data.xlsx found
)

:: Check if venv directory exists
if not exist "venv" (
    echo ERROR: Virtual environment 'venv' not found!
    echo Please create a virtual environment first.
    pause
    exit /b 1
) else (
    echo ✓ Virtual environment found
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)
echo ✓ Virtual environment activated

:: Install dependencies if needed
echo.
echo Checking dependencies...
pip install -r requirements.txt >nul 2>&1

:: Run the Flask application
echo.
echo Starting Flask application...
start /b python main.py

:: Wait a moment for the server to start
timeout /t 3 /nobreak >nul

:: Open browser to 127.0.0.1:5000
echo Opening browser at http://127.0.0.1:5000...
start http://127.0.0.1:5000

echo.
echo SSH Automation Server is now running!
echo You can access it at: http://127.0.0.1:5000
echo.
echo Press any key to keep this window open (this won't stop the server)...
pause >nul
