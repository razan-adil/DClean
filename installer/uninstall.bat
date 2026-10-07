@echo off
setlocal
cd /d "%~dp0"

echo ===========================================================================
echo                 DClean Windows Uninstallation Wizard
echo ===========================================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"

echo.
echo Press any key to exit...
pause >nul
