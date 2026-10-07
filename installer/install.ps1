# =====================================================================
# DClean - Windows Automated Installation Engine
# Installs DClean into %LOCALAPPDATA%\Programs\DClean (Zero Admin Rights Required)
# =====================================================================

param (
    [string]$TargetDir = "$env:LOCALAPPDATA\Programs\DClean",
    [switch]$SkipVenv,
    [switch]$NoContextMenu
)

$ErrorActionPreference = "Stop"

Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host "              DCLEAN WINDOWS INSTALLER & SETUP ENGINE" -ForegroundColor White
Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host "Target Installation Directory: $TargetDir" -ForegroundColor Yellow

# 1. Locate Python 3.10+
Write-Host "`n[1/6] Detecting Python Runtime..." -ForegroundColor Cyan
$PythonExe = $null

foreach ($cmd in @("py -3", "python", "py")) {
    try {
        $check = (& $cmd.Split()[0] ($cmd.Split() | Select-Object -Skip 1) -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") 2>$null
        if ($check -and [version]$check -ge [version]"3.10") {
            $PythonExe = $cmd
            Write-Host "  Found compatible Python $check ($cmd)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $PythonExe) {
    Write-Host "[ERROR] Python 3.10 or newer was not found on your system." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ (ensure 'Add python.exe to PATH' is checked)." -ForegroundColor Yellow
    exit 1
}

# 2. Prepare Directory Structure
Write-Host "`n[2/6] Setting up installation folders..." -ForegroundColor Cyan
$SourceRoot = (Resolve-Path "$PSScriptRoot\..").Path

$Directories = @(
    $TargetDir,
    "$TargetDir\bin",
    "$TargetDir\pipeline",
    "$TargetDir\models",
    "$TargetDir\config",
    "$TargetDir\installer\assets",
    "$TargetDir\CleanData"
)

foreach ($dir in $Directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# 3. Copy Application Artifacts
Write-Host "`n[3/6] Copying pipeline, models, and configuration files..." -ForegroundColor Cyan

Copy-Item "$SourceRoot\pipeline\*" "$TargetDir\pipeline" -Recurse -Force
Copy-Item "$SourceRoot\models\*" "$TargetDir\models" -Recurse -Force
Copy-Item "$SourceRoot\config\*" "$TargetDir\config" -Recurse -Force
Copy-Item "$SourceRoot\installer\*.py" "$TargetDir\installer" -Force
Copy-Item "$SourceRoot\installer\assets\*" "$TargetDir\installer\assets" -Recurse -Force
Copy-Item "$SourceRoot\requirements.txt" "$TargetDir\requirements.txt" -Force
if (Test-Path "$SourceRoot\dashboard.py") {
    Copy-Item "$SourceRoot\dashboard.py" "$TargetDir\dashboard.py" -Force
}

Write-Host "  Files successfully copied to $TargetDir" -ForegroundColor Green

# 4. Setup Dedicated Virtual Environment
$VenvDir = "$TargetDir\venv"
$VenvPython = "$VenvDir\Scripts\python.exe"
$VenvPythonw = "$VenvDir\Scripts\pythonw.exe"

if (-not $SkipVenv) {
    Write-Host "`n[4/6] Creating isolated virtual environment..." -ForegroundColor Cyan
    if (-not (Test-Path $VenvPython)) {
        $pyArgs = $PythonExe.Split()
        & $pyArgs[0] ($pyArgs | Select-Object -Skip 1) -m venv $VenvDir
    }

    Write-Host "  Installing dependencies from requirements.txt..." -ForegroundColor Cyan
    & $VenvPython -m pip install --quiet --upgrade pip
    & $VenvPython -m pip install --quiet -r "$TargetDir\requirements.txt"
    & $VenvPython -m pip install --quiet scikit-learn joblib streamlit pandas
    Write-Host "  Dependencies verified and installed." -ForegroundColor Green
} else {
    $VenvPython = "python"
    $VenvPythonw = "pythonw"
}

# 5. Create Executable Batch Wrappers
Write-Host "`n[5/6] Generating executable wrappers and shortcuts..." -ForegroundColor Cyan

# CLI batch wrapper
$DcleanBat = "$TargetDir\bin\dclean.bat"
@"
@echo off
"$VenvPython" "$TargetDir\installer\dclean_cli.py" %*
"@ | Set-Content -Path $DcleanBat -Encoding ASCII

# GUI batch wrapper
$DcleanGuiBat = "$TargetDir\bin\dclean-gui.bat"
@"
@echo off
start "" "$VenvPythonw" "$TargetDir\installer\dclean_launcher.py" %*
"@ | Set-Content -Path $DcleanGuiBat -Encoding ASCII

# Dashboard batch wrapper
$DcleanDashBat = "$TargetDir\bin\dclean-dashboard.bat"
@"
@echo off
"$VenvPython" -m streamlit run "$TargetDir\dashboard.py" %*
"@ | Set-Content -Path $DcleanDashBat -Encoding ASCII

# Desktop Shortcut
$WScriptShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WScriptShell.CreateShortcut("$DesktopPath\DClean.lnk")
$DesktopShortcut.TargetPath = "$VenvPythonw"
$DesktopShortcut.Arguments = "`"$TargetDir\installer\dclean_launcher.py`""
$DesktopShortcut.WorkingDirectory = $TargetDir
$DesktopShortcut.IconLocation = "$TargetDir\installer\assets\dclean_icon.ico, 0"
$DesktopShortcut.Description = "DClean Data Cleaning & Entity Resolution Studio"
$DesktopShortcut.Save()
Write-Host "  Created Desktop Shortcut: $DesktopPath\DClean.lnk" -ForegroundColor Green

# Start Menu Shortcut
$StartMenuPath = [Environment]::GetFolderPath("StartMenu") + "\Programs"
$StartMenuShortcut = $WScriptShell.CreateShortcut("$StartMenuPath\DClean.lnk")
$StartMenuShortcut.TargetPath = "$VenvPythonw"
$StartMenuShortcut.Arguments = "`"$TargetDir\installer\dclean_launcher.py`""
$StartMenuShortcut.WorkingDirectory = $TargetDir
$StartMenuShortcut.IconLocation = "$TargetDir\installer\assets\dclean_icon.ico, 0"
$StartMenuShortcut.Description = "DClean Data Cleaning & Entity Resolution Studio"
$StartMenuShortcut.Save()
Write-Host "  Created Start Menu Shortcut: $StartMenuPath\DClean.lnk" -ForegroundColor Green

# Add bin to User PATH
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$BinDir = "$TargetDir\bin"
if ($UserPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    Write-Host "  Added '$BinDir' to User PATH (dclean command available in new terminals)" -ForegroundColor Green
}

# 6. Windows Explorer Right-Click Context Menu
if (-not $NoContextMenu) {
    Write-Host "`n[6/6] Registering Windows Explorer Context Menu..." -ForegroundColor Cyan
    $Extensions = @(".xlsx", ".csv", ".xlsm")
    foreach ($ext in $Extensions) {
        $RegKeyPath = "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\DClean"
        $RegCmdPath = "$RegKeyPath\command"

        New-Item -Path $RegKeyPath -Force | Out-Null
        Set-ItemProperty -Path $RegKeyPath -Name "(Default)" -Value "Clean with DClean"
        Set-ItemProperty -Path $RegKeyPath -Name "Icon" -Value "$TargetDir\installer\assets\dclean_icon.ico"

        New-Item -Path $RegCmdPath -Force | Out-Null
        Set-ItemProperty -Path $RegCmdPath -Name "(Default)" -Value "`"$VenvPythonw`" `"$TargetDir\installer\dclean_launcher.py`" `"%1`""
    }
    Write-Host "  Registered 'Clean with DClean' on right-click for .xlsx, .csv, and .xlsm files." -ForegroundColor Green
}

# 7. Create Uninstaller Scripts
Copy-Item "$SourceRoot\installer\uninstall.ps1" "$TargetDir\uninstall.ps1" -Force
Copy-Item "$SourceRoot\installer\uninstall.bat" "$TargetDir\uninstall.bat" -Force

# Register in Windows Add/Remove Programs
$UninstallRegKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DClean"
New-Item -Path $UninstallRegKey -Force | Out-Null
Set-ItemProperty -Path $UninstallRegKey -Name "DisplayName" -Value "DClean Data Cleaning Pipeline"
Set-ItemProperty -Path $UninstallRegKey -Name "DisplayVersion" -Value "1.0.0"
Set-ItemProperty -Path $UninstallRegKey -Name "Publisher" -Value "DClean Team"
Set-ItemProperty -Path $UninstallRegKey -Name "DisplayIcon" -Value "$TargetDir\installer\assets\dclean_icon.ico"
Set-ItemProperty -Path $UninstallRegKey -Name "UninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$TargetDir\uninstall.ps1`""
Set-ItemProperty -Path $UninstallRegKey -Name "InstallLocation" -Value $TargetDir

Write-Host "`n===========================================================================" -ForegroundColor Green
Write-Host "                 DCLEAN INSTALLED SUCCESSFULLY!" -ForegroundColor White
Write-Host "===========================================================================" -ForegroundColor Green
Write-Host "You can now:"
Write-Host "  1. Launch DClean from your Desktop shortcut or Start Menu."
Write-Host "  2. Right-click any Excel or CSV file -> click 'Clean with DClean'."
Write-Host "  3. Open any terminal (PowerShell / CMD) and type 'dclean --help'."
Write-Host "===========================================================================`n"
