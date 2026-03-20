; Inno Setup Script for Hantech Document Generator
; Requires Inno Setup 6.x

#define MyAppName "Kreator Dokumentow Hantech"
#define MyAppPublisher "Hantech"
#define MyAppExeName "OfferGenerator.exe"

; Version passed from CI via /DMyAppVersion=x.y.z or defaults to 1.0.0
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{B5F8E2A1-3C4D-4E6F-A1B2-9D8E7F6C5A4B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HantechDokumenty
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=HantechDokumenty-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayName={#MyAppName}
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application directory (PyInstaller --onedir output)
Source: "dist\OfferGenerator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Odinstaluj {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Show info about settings location after install
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Settings are stored in %APPDATA%\HantechDokumenty - no action needed
  end;
end;
