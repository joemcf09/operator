; ---------------------------------------------------------------------------
;  Operator — Ferry, Cargo & ACMI
;  Inno Setup 6 script. Build the application first (build.bat), then either
;  let build.bat compile this, or run:
;      "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\operator.iss
;  Output: installer\Output\Operator-Setup-<version>.exe
; ---------------------------------------------------------------------------

#define AppName      "Operator"
#define AppFullName  "Operator — Ferry, Cargo & ACMI"
#define AppVersion   "1.8.0"
#define AppPublisher "Operator"
#define AppExe       "Operator.exe"
#define AppUrl       "https://127.0.0.1:8123"

[Setup]
AppId={{7C7C1C2E-4E7C-4C2B-9F0E-0B7A3D1B6A21}
AppName={#AppFullName}
AppVersion={#AppVersion}
AppVerName={#AppFullName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppFullName} setup
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppFullName}
UninstallDisplayIcon={app}\{#AppExe}
DisableProgramGroupPage=yes
DisableWelcomePage=no
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=Operator-Setup-{#AppVersion}
SetupIconFile=..\brand\favicon.ico
WizardStyle=modern
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.bmp
WizardImageStretch=no
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
LicenseFile=..\LICENSE.txt
InfoBeforeFile=readme-before.txt
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no
AppMutex=OperatorRunningMutex
SetupMutex=OperatorSetupMutex

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startmenu";   Description: "Create a Start menu shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "..\dist\Operator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\README.txt";     DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\FIRST-RUN.txt";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\CHANGELOG.txt";  DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\CHARTER-REFERENCE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md";            DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt";          DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Sweep the previous build's runtime files so nothing stale is left behind on an
; upgrade. The save folder is deliberately untouched.
Type: filesandordirs; Name: "{app}\_internal"
Type: files;          Name: "{app}\*.pyd"
Type: files;          Name: "{app}\*.dll"

[Dirs]
Name: "{app}\save"; Permissions: users-modify

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExe}"; Comment: "Run a ferry, cargo and ACMI operation"; Tasks: startmenu
Name: "{group}\{#AppName} (browser)"; Filename: "{app}\{#AppExe}"; Parameters: "--browser"; Comment: "Open in your web browser instead of the app window"; Tasks: startmenu
Name: "{group}\Operator saves";       Filename: "{app}\save";      Tasks: startmenu
Name: "{group}\Read me";              Filename: "{app}\README.txt"; Tasks: startmenu
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}";  Tasks: startmenu
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExe}"; Comment: "Run a ferry, cargo and ACMI operation"; Tasks: desktopicon

[Run]
Filename: "{app}\FIRST-RUN.txt"; Description: "Open the first-run guide"; Flags: shellexec postinstall skipifsilent unchecked
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: files;          Name: "{app}\operator-log.txt"

[Code]
var
  KeepSaves: Boolean;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  { Carry saves over from a portable copy the first time, if the user points at one. }
  if CurStep = ssPostInstall then
  begin
    if not DirExists(ExpandConstant('{app}\save')) then
      CreateDir(ExpandConstant('{app}\save'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    KeepSaves := True;
    if DirExists(ExpandConstant('{app}\save')) then
      KeepSaves := MsgBox('Keep your Operator save files?' + #13#10#13#10 +
                          ExpandConstant('{app}\save') + #13#10#13#10 +
                          'Choose No to delete them along with the program.',
                          mbConfirmation, MB_YESNO) = IDYES;
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if not KeepSaves then
      DelTree(ExpandConstant('{app}\save'), True, True, True);
  end;
end;
