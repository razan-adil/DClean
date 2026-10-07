@echo off
setlocal

echo ===========================================================================
echo                   DClean Production Build Engine (.exe)
echo ===========================================================================
echo.

cd /d "%~dp0\.."

:: 1. Verify / Locate Python runtime
echo [1/4] Checking Python environment...
py -3.14 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3.14"
) else (
    set "PY_CMD=python"
)

:: 2. Verify / Install PyInstaller
echo [2/4] Verifying PyInstaller...
%PY_CMD% -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    %PY_CMD% -m pip install --quiet pyinstaller
)

:: 3. Run PyInstaller to build standalone executable bundle
echo [3/4] Compiling standalone DClean.exe application bundle...
echo This may take 30-60 seconds...
%PY_CMD% -m PyInstaller --clean --noconfirm "installer\dclean.spec"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PyInstaller compilation failed!
    exit /b %ERRORLEVEL%
)

if not exist "dist\DClean\DClean.exe" (
    echo.
    echo [ERROR] Expected output dist\DClean\DClean.exe not found!
    exit /b 1
)
echo Standalone binary built successfully at: dist\DClean\DClean.exe

:: 4. Locate Inno Setup Compiler
echo [4/4] Compiling single-file Windows Installer (DClean-Setup-v1.0.exe)...

set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\iscc.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Program Files\Inno Setup 6\iscc.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\iscc.exe"

if not exist "%ISCC_PATH%" (
    echo.
    echo [WARNING] Inno Setup compiler (iscc.exe) not found.
    echo Standalone bundle dist\DClean\DClean.exe is ready,
    echo but single-file installer could not be generated.
    exit /b 1
)

"%ISCC_PATH%" "installer\dclean_setup.iss"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Inno Setup compilation failed!
    exit /b %ERRORLEVEL%
)

echo.
echo ===========================================================================
echo                   DCLEAN BUILD COMPLETE!
echo ===========================================================================
echo Standalone App:      dist\DClean\DClean.exe
echo Windows Setup File:  dist\DClean-Setup-v1.0.exe
echo.
echo You can now distribute dist\DClean-Setup-v1.0.exe to any Windows user!
echo ===========================================================================
