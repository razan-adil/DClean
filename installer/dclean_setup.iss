; =====================================================================
; DClean - Inno Setup Compiler Script
; Packages standalone PyInstaller distribution into a single-file installer:
; dist\DClean-Setup-v1.0.exe
; Requires: Inno Setup 6 (https://jrsoftware.org/isdl.php)
; =====================================================================

#define MyAppName "DClean"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "DClean Team"
#define MyAppURL "https://github.com/M2sk2/DClean"
#define MyAppExeName "DClean.exe"

[Setup]
AppId={{D9B38F72-3E6B-4D88-9F31-4A59A1D019F8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\DClean
DisableDirPage=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=DClean-Setup-v1.0
SetupIconFile=assets\dclean_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "contextmenu"; Description: "Add 'Clean with DClean' to Windows Explorer right-click menu"; GroupDescription: "Windows Explorer Integration:"

[Files]
; Standalone PyInstaller application bundle
Source: "..\dist\DClean\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Direct installer assets for shell icons
Source: "assets\*"; DestDir: "{app}\installer\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Windows Start Menu (Indexed by Windows Search)
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; IconIndex: 0; Tasks: desktopicon

[Registry]
; Universal context menu with file extension filter (works across Windows 10 & 11)
Root: HKCU; Subkey: "Software\Classes\*\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\DClean"; ValueType: string; ValueName: "AppliesTo"; ValueData: "System.FileExtension:=.xlsx OR System.FileExtension:=.csv OR System.FileExtension:=.xlsm"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

; Excel ProgID associations (ensures direct appearance when Excel is installed)
Root: HKCU; Subkey: "Software\Classes\Excel.Sheet.12\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Excel.Sheet.12\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Excel.Sheet.12\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

Root: HKCU; Subkey: "Software\Classes\Excel.CSV\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Excel.CSV\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Excel.CSV\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

Root: HKCU; Subkey: "Software\Classes\Excel.SheetMacroEnabled.12\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Excel.SheetMacroEnabled.12\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\Excel.SheetMacroEnabled.12\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

; SystemFileAssociations (.xlsx, .csv, .xlsm)
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsx\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.csv\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\DClean"; ValueType: string; ValueName: ""; ValueData: "Clean with DClean"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\DClean"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName},0"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.xlsm\shell\DClean\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: contextmenu

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: postinstall nowait skipifsilent
