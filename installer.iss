; Inno Setup script for the Glosor desktop app. Build Glosor.exe with PyInstaller first,
; then run: iscc installer.iss   (output: dist\GlosorSetup.exe)

#ifndef AppVersion
  #define AppVersion "1.0"
#endif

[Setup]
; Keep AppId the same across versions so a new installer upgrades the old install.
AppId={{D36367E4-DC76-461B-9CB8-85C4738E8F48}
AppName=Glosor
AppVersion={#AppVersion}
AppPublisher=Herman
DefaultDirName={autopf}\Glosor
DefaultGroupName=Glosor
DisableProgramGroupPage=yes
; Install for the current user only, so no administrator password is needed.
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=GlosorSetup
UninstallDisplayIcon={app}\Glosor.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Glosor.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Glosor"; Filename: "{app}\Glosor.exe"
Name: "{autodesktop}\Glosor"; Filename: "{app}\Glosor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Glosor.exe"; Description: "{cm:LaunchProgram,Glosor}"; Flags: nowait postinstall skipifsilent
