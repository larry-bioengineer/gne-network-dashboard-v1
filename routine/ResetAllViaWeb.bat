@echo off
echo Starting Reset Down Port Only operation via web API...
echo.

REM Set the domain and port using SERVER_PORT environment variable
set DOMAIN=127.0.0.1
set ENDPOINT=/api/network/reset_all_locations_sse

REM Use SERVER_PORT environment variable, default to 5000 if not set
if "%SERVER_PORT%"=="" set SERVER_PORT=5000

echo Using port: %SERVER_PORT%

REM Make the curl request to reset all locations
curl -X POST ^
  -H "Content-Type: application/json" ^
  -d "{\"timeout\": 30}" ^
  http://%DOMAIN%:%SERVER_PORT%%ENDPOINT%

echo.
echo Operation completed.
pause
