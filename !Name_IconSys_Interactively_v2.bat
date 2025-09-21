@echo off
:: Double-click to run the 2-line-aware icon.sys namer recursively.
setlocal
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
python "%SCRIPT_DIR%\name_icons_interactive_v2.py" "%SCRIPT_DIR%"
echo.
echo Done. Press any key to exit.
pause >nul
