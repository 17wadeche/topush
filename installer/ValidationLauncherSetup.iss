[Setup]
AppName=Validation UI Launcher
AppVersion=1.0.0
DefaultDirName={localappdata}\MedtronicValidationTool
DefaultGroupName=Validation
PrivilegesRequired=lowest
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputBaseFilename=ValidationLauncherSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "C:\topush\dist\ValidationLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Validation UI"; Filename: "{app}\ValidationLauncher.exe"
