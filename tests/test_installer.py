"""
Unit & Integration Tests for the DClean Windows Installer, Launcher & CLI.
"""

import os
import sys
import pytest

# Ensure workspace root is on sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

def test_installer_assets_and_scripts_exist():
    installer_dir = os.path.join(WORKSPACE_ROOT, "installer")
    assert os.path.isdir(installer_dir), "installer directory must exist"

    # Icon
    icon_path = os.path.join(installer_dir, "assets", "dclean_icon.ico")
    assert os.path.exists(icon_path), "dclean_icon.ico must exist"
    assert os.path.getsize(icon_path) > 1000, "Icon file must be non-empty"

    # PowerShell and Batch scripts
    assert os.path.exists(os.path.join(installer_dir, "install.ps1")), "install.ps1 must exist"
    assert os.path.exists(os.path.join(installer_dir, "install.bat")), "install.bat must exist"
    assert os.path.exists(os.path.join(installer_dir, "uninstall.ps1")), "uninstall.ps1 must exist"
    assert os.path.exists(os.path.join(installer_dir, "uninstall.bat")), "uninstall.bat must exist"

    # Packaging configs
    assert os.path.exists(os.path.join(installer_dir, "dclean_setup.iss")), "Inno setup script must exist"
    assert os.path.exists(os.path.join(installer_dir, "dclean.spec")), "PyInstaller spec must exist"

def test_dclean_cli_argparser():
    from installer.dclean_cli import main
    # Ensure module imports cleanly and commands are mapped
    assert callable(main)

def test_dclean_cli_validate_command(capsys):
    from installer.dclean_cli import cmd_validate
    import argparse
    args = argparse.Namespace(contract="config/workshop_contract.yaml")
    cmd_validate(args)
    captured = capsys.readouterr()
    assert "[VALID]" in captured.out

def test_dclean_cli_diff_command(capsys):
    from installer.dclean_cli import cmd_diff
    import argparse
    args = argparse.Namespace(
        input="RawData/Distraction_Era_Workshop_Dataset.xlsx",
        contract="config/workshop_contract.yaml"
    )
    cmd_diff(args)
    captured = capsys.readouterr()
    assert "Audit Diff" in captured.out
    assert "Compliant:" in captured.out

def test_dclean_launcher_headless_clean_missing_file():
    from installer.dclean_launcher import run_headless_clean
    # Passing a non-existent file should safely return False
    res = run_headless_clean("non_existent_file_xyz123.xlsx")
    assert res is False

def test_powershell_installer_syntax():
    """Verify that install.ps1 and uninstall.ps1 have valid PowerShell syntax."""
    import subprocess
    ps1_files = [
        os.path.join(WORKSPACE_ROOT, "installer", "install.ps1"),
        os.path.join(WORKSPACE_ROOT, "installer", "uninstall.ps1")
    ]
    for ps1 in ps1_files:
        cmd = ["powershell", "-NoProfile", "-Command", f"[System.Management.Automation.Language.Parser]::ParseFile('{ps1}', [ref]$null, [ref]$null)"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in {ps1}: {res.stderr}"

def test_dashboard_file_syntax_and_runner_connection():
    """Verify dashboard.py has valid syntax and references PipelineRunner correctly."""
    import ast
    dashboard_path = os.path.join(WORKSPACE_ROOT, "dashboard.py")
    assert os.path.exists(dashboard_path), "dashboard.py must exist in root directory"
    with open(dashboard_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="dashboard.py")
    assert tree is not None
    # Check that PipelineRunner is imported
    imported_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.append(alias.name)
    assert "PipelineRunner" in imported_names, "dashboard.py must import PipelineRunner"


def test_build_script_and_setup_shortcuts():
    """Verify build_installer.bat exists and dclean_setup.iss configures Start Menu and Desktop shortcuts."""
    installer_dir = os.path.join(WORKSPACE_ROOT, "installer")
    build_bat = os.path.join(installer_dir, "build_installer.bat")
    assert os.path.exists(build_bat), "build_installer.bat must exist"

    iss_file = os.path.join(installer_dir, "dclean_setup.iss")
    with open(iss_file, "r", encoding="utf-8") as f:
        iss_content = f.read()

    assert "{autoprograms}\\{#MyAppName}" in iss_content or "{autoprograms}" in iss_content, "Start Menu shortcut must be configured"
    assert "{autodesktop}" in iss_content, "Desktop shortcut must be configured"
    assert "DClean-Setup-v1.0" in iss_content, "Output filename must be configured"


def test_compiled_executables_exist():
    """Verify that the standalone executable and single-file setup wizard were built."""
    standalone_exe = os.path.join(WORKSPACE_ROOT, "dist", "DClean", "DClean.exe")
    setup_exe = os.path.join(WORKSPACE_ROOT, "dist", "DClean-Setup-v1.0.exe")

    assert os.path.exists(standalone_exe), "dist/DClean/DClean.exe must exist"
    assert os.path.getsize(standalone_exe) > 10_000_000, "DClean.exe must be a valid binary"

    assert os.path.exists(setup_exe), "dist/DClean-Setup-v1.0.exe must exist"
    assert os.path.getsize(setup_exe) > 50_000_000, "DClean-Setup-v1.0.exe must be a valid setup wizard"

