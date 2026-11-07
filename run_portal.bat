@echo off
title Electric Operation Department - Howrah Division Web Portal
color 1F
echo =========================================================================
echo    ELECTRIC OPERATION DEPARTMENT, HOWRAH DIVISION - EASTERN RAILWAY
echo               Site & Management Web Application System
echo =========================================================================
echo.
echo Starting Application Server on http://localhost:5000 ...
echo.

set "PY_EXE=python"
if exist "C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Scripts\python.exe" (
    set "PY_EXE=C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Scripts\python.exe"
)

"%PY_EXE%" app.py
if %errorlevel% neq 0 (
    echo.
    echo Retrying with default system python...
    python app.py
)
pause
