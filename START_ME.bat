@echo off
echo Starting SSH Automation Server...
echo.

:: Check if .env file exists
if not exist ".env" goto no_env
echo ✓ .env file found
:: Load environment variables from .env file
for /f "usebackq tokens=*" %%i in (".env") do (
    for /f "tokens=1,* delims==" %%a in ("%%i") do (
        set %%a=%%b
    )
)
goto env_check_complete

:no_env
echo WARNING: .env file not found!
echo Continuing without .env file...
echo.
set SERVER_PORT=5000

:env_check_complete
:: Set default port if SERVER_PORT is not defined
set port_check=%SERVER_PORT%
if "%port_check%"=="" set SERVER_PORT=5000

:: Check if config_file/data.xlsx exists
if not exist "config_file\data.xlsx" goto no_data_file
echo ✓ config_file/data.xlsx found
goto check_venv

:no_data_file
echo ERROR: config_file/data.xlsx not found!
echo Please ensure data.xlsx exists in the config_file directory.
pause
exit /b 1

:check_venv
:: Check if venv directory exists
if not exist "venv" goto create_venv
echo ✓ Virtual environment found
goto activate_existing_venv

:create_venv
echo Virtual environment 'venv' not found!
echo Creating virtual environment...
python -m venv venv
set venv_result=%errorlevel%
if not %venv_result%==0 goto venv_creation_error
echo ✓ Virtual environment created
goto install_new_deps

:venv_creation_error
echo ERROR: Failed to create virtual environment!
echo Please ensure Python is installed and try again.
pause
exit /b 1

:install_new_deps
:: Activate the newly created virtual environment immediately
echo Activating new virtual environment...
call venv\Scripts\activate.bat
set venv_activate_result=%errorlevel%
if not %venv_activate_result%==0 goto venv_activation_error
echo ✓ Virtual environment activated

:: Install dependencies for the newly created virtual environment
echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
set deps_result=%errorlevel%
if not %deps_result%==0 goto deps_installation_error
echo ✓ All dependencies installed successfully
goto verify_dependencies

:activate_existing_venv
:: Activate existing virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
set venv_activate_result=%errorlevel%
if not %venv_activate_result%==0 goto venv_activation_error
echo ✓ Virtual environment activated

:: Install/update dependencies for existing virtual environment
echo.
echo Updating dependencies...
pip install -r requirements.txt
set deps_result=%errorlevel%
if not %deps_result%==0 goto deps_installation_error
echo ✓ Dependencies updated successfully
goto verify_dependencies

:venv_activation_error
echo ERROR: Failed to activate virtual environment!
pause
exit /b 1

:deps_installation_error
echo ERROR: Dependencies installation failed!
echo Please check your internet connection and try again.
pause
exit /b 1

:verify_dependencies
:: Verify dependencies before starting Flask
echo.
echo Verifying dependencies...

:: Check if virtual environment python exists
if not exist "venv\Scripts\python.exe" goto no_python_exe
goto check_flask

:no_python_exe
echo ERROR: Virtual environment Python executable not found!
pause
exit /b 1

:check_flask
echo Checking Flask...
venv\Scripts\python.exe -c "import flask" >nul 2>&1
set flask_check=%errorlevel%
if not %flask_check%==0 goto flask_not_found
goto check_paramiko

:flask_not_found
echo ERROR: Flask not available - terminating
pause
exit /b 1

:check_paramiko
echo Checking Paramiko...
venv\Scripts\python.exe -c "import paramiko" >nul 2>&1
set paramiko_check=%errorlevel%
if not %paramiko_check%==0 goto paramiko_not_found
goto start_flask

:paramiko_not_found
echo ERROR: Paramiko not available - terminating
pause
exit /b 1

:start_flask
echo ✓ All critical dependencies verified

:: Run the Flask application
echo.
echo Starting Flask application...

:: Use the virtual environment's Python to run the Flask app
start /b venv\Scripts\python.exe main.py

:: Wait a moment for the server to start
timeout /t 3 /nobreak >nul

:: Open browser to 127.0.0.1 with dynamic port
echo Opening browser at http://127.0.0.1:%SERVER_PORT%...
start http://127.0.0.1:%SERVER_PORT%

echo.
echo SSH Automation Server is now running!
echo You can access it at: http://127.0.0.1:%SERVER_PORT%
echo.
echo Press any key to keep this window open (this won't stop the server)...
pause >nul
