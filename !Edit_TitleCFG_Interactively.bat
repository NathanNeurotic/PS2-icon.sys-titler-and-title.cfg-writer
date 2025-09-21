@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
python "%SCRIPT_DIR%\edit_title_cfg_interactive.py" "%SCRIPT_DIR%"
echo.
echo Done. Press any key to exit.
pause >nul
