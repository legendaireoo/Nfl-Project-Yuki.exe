@echo off
REM ===================================================================
REM  Yuki.exe - one-click launcher for Windows
REM  Double-click this file to start the NFL analytics dashboard.
REM  It finds Python, launches the server, and opens your browser.
REM ===================================================================
setlocal
cd /d "%~dp0"

echo Starting Yuki.exe ...

REM Find a Python interpreter (py launcher preferred, then python/python3).
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
    goto run
)
where python >nul 2>nul
if %errorlevel%==0 (
    set "PY=python"
    goto run
)
where python3 >nul 2>nul
if %errorlevel%==0 (
    set "PY=python3"
    goto run
)

echo.
echo [ERROR] Python 3 was not found on this computer.
echo         Install it from https://www.python.org/downloads/
echo         (tick "Add Python to PATH" during setup), then run this again.
echo.
pause
exit /b 1

:run
%PY% launch.py
echo.
pause
endlocal
