@echo off
setlocal
cd /d "%~dp0"

echo ===========================================================================
echo                 DClean Windows Installation Wizard
echo ===========================================================================
echo.
echo Launching automated setup engine...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation failed with error code %ERRORLEVEL%.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Press any key to exit setup...
pause >nul
