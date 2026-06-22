; ===== سكربت Inno Setup لإنشاء مُثبّت ويندوز =====
; يُبنى بعد توليد المجلد dist\ShowroomColor عبر PyInstaller.
; افتح هذا الملف في Inno Setup Compiler ثم Build.

#define AppName "نظام إدارة معرض الدراجات النارية"
#define AppNameEn "ShowroomERP"
#define AppVersion "1.0.0"
#define AppPublisher "Showroom ERP"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppNameEn}
DefaultGroupName={#AppName}
OutputBaseFilename=ShowroomERP_Setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Files]
; ناتج PyInstaller (وضع onedir): انسخ كامل مجلد dist\ShowroomERP
Source: "..\dist\ShowroomERP\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\ShowroomERP.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\ShowroomERP.exe"

[Run]
Filename: "{app}\ShowroomERP.exe"; Description: "تشغيل البرنامج الآن"; Flags: nowait postinstall skipifsilent
