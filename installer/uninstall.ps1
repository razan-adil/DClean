# =====================================================================
# DClean - Clean Uninstallation Engine
# Safely removes DClean files, shortcuts, registry keys, and PATH entries
# =====================================================================

param (
    [string]$TargetDir = "$env:LOCALAPPDATA\Programs\DClean",
    [switch]$Force
)

Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host "                DCLEAN UNINSTALLATION WIZARD" -ForegroundColor White
Write-Host "===========================================================================" -ForegroundColor Cyan

if (-not $Force) {
    $confirm = Read-Host "Are you sure you want to completely remove DClean? (y/N)"
    if ($confirm -notmatch "^[Yy]$") {
        Write-Host "Uninstallation cancelled." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`n[1/4] Removing Desktop & Start Menu shortcuts..." -ForegroundColor Cyan
$DesktopShortcut = "$([Environment]::GetFolderPath('Desktop'))\DClean.lnk"
if (Test-Path $DesktopShortcut) {
    Remove-Item $DesktopShortcut -Force
    Write-Host "  Removed: $DesktopShortcut" -ForegroundColor Green
}

$StartMenuShortcut = "$([Environment]::GetFolderPath('StartMenu'))\Programs\DClean.lnk"
if (Test-Path $StartMenuShortcut) {
    Remove-Item $StartMenuShortcut -Force
    Write-Host "  Removed: $StartMenuShortcut" -ForegroundColor Green
}

Write-Host "`n[2/4] Removing Windows Explorer Context Menu & Registry entries..." -ForegroundColor Cyan
$Extensions = @(".xlsx", ".csv", ".xlsm")
foreach ($ext in $Extensions) {
    $RegKey = "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\DClean"
    if (Test-Path $RegKey) {
        Remove-Item $RegKey -Recurse -Force
        Write-Host "  Removed Context Menu for $ext" -ForegroundColor Green
    }
}

$UninstallReg = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\DClean"
if (Test-Path $UninstallReg) {
    Remove-Item $UninstallReg -Recurse -Force
    Write-Host "  Removed Add/Remove Programs entry" -ForegroundColor Green
}

Write-Host "`n[3/4] Cleaning User PATH environment variable..." -ForegroundColor Cyan
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$BinDir = "$TargetDir\bin"
if ($UserPath -like "*$BinDir*") {
    $NewPath = ($UserPath.Split(';') | Where-Object { $_ -and $_ -ne $BinDir }) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "  Removed '$BinDir' from User PATH" -ForegroundColor Green
}

Write-Host "`n[4/4] Removing installation directory: $TargetDir..." -ForegroundColor Cyan
if (Test-Path $TargetDir) {
    # If uninstaller is running from within target directory, schedule deletion
    try {
        Remove-Item $TargetDir -Recurse -Force -ErrorAction Stop
        Write-Host "  Removed $TargetDir" -ForegroundColor Green
    } catch {
        # Fallback: remove everything except running script
        Get-ChildItem -Path $TargetDir -Exclude "uninstall.*" -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "  Cleaned files in $TargetDir (remaining temporary files will be cleaned upon restart)" -ForegroundColor Yellow
    }
}

Write-Host "`n===========================================================================" -ForegroundColor Green
Write-Host "            DCLEAN HAS BEEN SUCCESSFULLY UNINSTALLED" -ForegroundColor White
Write-Host "===========================================================================`n"
