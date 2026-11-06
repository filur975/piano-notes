; Inno Setup script for the Noter desktop app. Build Noter.exe with PyInstaller first,
; then run: iscc installer.iss   (output: dist\NoterSetup.exe)

#ifndef AppVersion
  #define AppVersion "1.0"
#endif

[Setup]
; Keep AppId the same across versions so a new installer upgrades the old install.
AppId={{ED890D23-9600-4E39-BADE-FBF4B4B1C420}
AppName=Noter
AppVersion={#AppVersion}
AppPublisher=Herman
DefaultDirName={autopf}\Noter
DefaultGroupName=Noter
DisableProgramGroupPage=yes
; Install for the current user only, so no administrator password is needed.
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=NoterSetup
UninstallDisplayIcon={app}\Noter.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Noter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Noter"; Filename: "{app}\Noter.exe"
Name: "{autodesktop}\Noter"; Filename: "{app}\Noter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Noter.exe"; Description: "{cm:LaunchProgram,Noter}"; Flags: nowait postinstall skipifsilent
