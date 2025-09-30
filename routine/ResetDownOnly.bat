@echo off
echo Starting Reset Down Only Script...
echo.

:: Check if .env file exists
if not exist "..\.env" goto no_env
echo ✓ .env file found
:: Load environment variables from .env file
for /f "usebackq tokens=*" %%i in ("..\.env") do (
    for /f "tokens=1,* delims==" %%a in ("%%i") do (
        set %%a=%%b
    )
)
goto env_check_complete

:no_env
echo WARNING: .env file not found!
echo Continuing without .env file...
echo.

:env_check_complete
:: Check if config_file/data.xlsx exists
if not exist "..\config_file\data.xlsx" goto no_data_file
echo ✓ config_file/data.xlsx found
goto check_venv

:no_data_file
echo ERROR: config_file/data.xlsx not found!
echo Please ensure data.xlsx exists in the config_file directory.
pause
exit /b 1

:check_venv
:: Check if venv directory exists
if not exist "..\venv" goto create_venv
echo ✓ Virtual environment found
goto activate_existing_venv

:create_venv
echo Virtual environment 'venv' not found!
echo Creating virtual environment...
cd ..
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
call ..\venv\Scripts\activate.bat
set venv_activate_result=%errorlevel%
if not %venv_activate_result%==0 goto venv_activation_error
echo ✓ Virtual environment activated

:: Install dependencies for the newly created virtual environment
echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r ..\requirements.txt
set deps_result=%errorlevel%
if not %deps_result%==0 goto deps_installation_error
echo ✓ All dependencies installed successfully
goto verify_dependencies

:activate_existing_venv
:: Activate existing virtual environment
echo Activating virtual environment...
call ..\venv\Scripts\activate.bat
set venv_activate_result=%errorlevel%
if not %venv_activate_result%==0 goto venv_activation_error
echo ✓ Virtual environment activated

:: Install/update dependencies for existing virtual environment
echo.
echo Updating dependencies...
pip install -r ..\requirements.txt
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
:: Verify dependencies before running the script
echo.
echo Verifying dependencies...

:: Check if virtual environment python exists
if not exist "..\venv\Scripts\python.exe" goto no_python_exe
goto check_pandas

:no_python_exe
echo ERROR: Virtual environment Python executable not found!
pause
exit /b 1

:check_pandas
echo Checking Pandas...
..\venv\Scripts\python.exe -c "import pandas" >nul 2>&1
set pandas_check=%errorlevel%
if not %pandas_check%==0 goto pandas_not_found
goto check_paramiko

:pandas_not_found
echo ERROR: Pandas not available - terminating
pause
exit /b 1

:check_paramiko
echo Checking Paramiko...
..\venv\Scripts\python.exe -c "import paramiko" >nul 2>&1
set paramiko_check=%errorlevel%
if not %paramiko_check%==0 goto paramiko_not_found
goto run_reset_script

:paramiko_not_found
echo ERROR: Paramiko not available - terminating
pause
exit /b 1

:run_reset_script
echo ✓ All critical dependencies verified

:: Run the ResetDownOnly.py script
echo.
echo Starting Reset Down Only Script...
echo.

:: Use the virtual environment's Python to run the reset script
..\venv\Scripts\python.exe ResetDownOnly.py

:: Check the exit code and display appropriate message
set script_result=%errorlevel%
if %script_result%==0 (
    echo.
    echo ✓ Reset Down Only Script completed successfully!
) else if %script_result%==1 (
    echo.
    echo ❌ Reset Down Only Script failed with errors!
) else if %script_result%==2 (
    echo.
    echo ⚠️ Reset Down Only Script completed with some failures!
) else (
    echo.
    echo ❌ Reset Down Only Script exited with code %script_result%
)

echo.
echo Press any key to exit...
pause >nul
