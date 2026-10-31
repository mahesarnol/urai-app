; Installer Urai App (Inno Setup 6). Dirakit otomatis oleh GitHub Actions:
;   iscc /DAppVersion=3.0.0 packaging\installer.iss
; Dipasang per pengguna (tanpa hak admin) ke %LOCALAPPDATA%\Programs\Urai App ({autopf} pada mode per pengguna).
; Bila pengguna memilih "untuk semua pengguna" di awal, {autopf} menjadi Program Files.
; Dua bahasa: English (bawaan) dan Bahasa Indonesia, dipilih di awal pemasangan.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Urai App"
#define AppExe "Urai App.exe"
#define AppPublisher "mahesarnol"
#define AppRepo "https://github.com/mahesarnol/urai-app"

[Setup]
AppId={{6F2B7C0E-3D7A-4E3B-9A51-5B0E2C7D8A31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppRepo}
AppSupportURL={#AppRepo}/issues
AppUpdatesURL={#AppRepo}/releases
AppCopyright=(c) 2026 mahesarnol. MIT License.
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=UraiApp-{#AppVersion}-Setup
SetupIconFile=urai.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=..\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription=Installer {#AppName}
; Jendela pilihan bahasa selalu tampil, dengan English terpilih lebih dulu.
ShowLanguageDialog=yes
LanguageDetectionMethod=none

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "id"; MessagesFile: "compiler:Default.isl"

[LangOptions]
id.LanguageName=Bahasa Indonesia
id.LanguageID=$0421

; Inno Setup tidak menyertakan bahasa Indonesia resmi; pesan yang paling sering terlihat diterjemahkan di sini.
; Awalan "id." membuat pesan ini hanya berlaku untuk bahasa Indonesia; English memakai Default.isl apa adanya.
[Messages]
id.SetupAppTitle=Pemasangan
id.SetupWindowTitle=Pemasangan %1
id.SelectLanguageTitle=Pilih Bahasa Pemasangan
id.SelectLanguageLabel=Pilih bahasa yang dipakai selama pemasangan.
id.ButtonBack=< &Kembali
id.ButtonNext=&Lanjut >
id.ButtonInstall=&Pasang
id.ButtonOK=OK
id.ButtonCancel=Batal
id.ButtonYes=&Ya
id.ButtonNo=&Tidak
id.ButtonFinish=&Selesai
id.ButtonBrowse=&Telusuri...
id.ButtonWizardBrowse=T&elusuri...
id.ExitSetupTitle=Keluar dari Pemasangan
id.ExitSetupMessage=Pemasangan belum selesai. Jika keluar sekarang, aplikasi tidak akan terpasang.%n%nKeluar dari Pemasangan?
id.WizardLicense=Perjanjian Lisensi
id.LicenseLabel=Bacalah informasi penting berikut sebelum melanjutkan.
id.LicenseLabel3=Urai App adalah perangkat lunak open source berlisensi MIT. Silakan baca lisensinya.
id.LicenseAccepted=Saya &menerima perjanjian ini
id.LicenseNotAccepted=Saya &tidak menerima perjanjian ini
id.WizardSelectDir=Pilih Lokasi Pemasangan
id.SelectDirDesc=Di mana [name] akan dipasang?
id.SelectDirLabel3=[name] akan dipasang ke folder berikut.
id.SelectDirBrowseLabel=Tekan Lanjut untuk meneruskan. Untuk memilih folder lain, tekan Telusuri.
id.WizardSelectTasks=Pilih Tugas Tambahan
id.SelectTasksDesc=Tugas tambahan apa yang perlu dilakukan?
id.SelectTasksLabel2=Pilih tugas tambahan yang diinginkan, lalu tekan Lanjut.
id.WizardReady=Siap Memasang
id.ReadyLabel1=[name] siap dipasang di komputer ini.
id.ReadyLabel2a=Tekan Pasang untuk mulai, atau Kembali untuk mengubah pilihan.
id.ReadyLabel2b=Tekan Pasang untuk mulai.
id.WizardPreparing=Menyiapkan Pemasangan
id.WizardInstalling=Memasang
id.InstallingLabel=Tunggu sebentar, [name] sedang dipasang di komputer ini.
id.FinishedHeadingLabel=Pemasangan [name] selesai
id.FinishedLabelNoIcons=[name] sudah terpasang di komputer ini.
id.FinishedLabel=[name] sudah terpasang. Buka lewat menu Start atau ikon yang dibuat.
id.ClickFinish=Tekan Selesai untuk menutup.
id.WelcomeLabel1=Selamat datang di Pemasangan [name]
id.WelcomeLabel2=[name/ver] akan dipasang di komputer ini.%n%nSebaiknya tutup aplikasi lain sebelum melanjutkan.
id.StatusExtractFiles=Menyalin file...
id.StatusCreateIcons=Membuat pintasan...
id.StatusUninstalling=Menghapus %1...
id.ConfirmUninstall=Hapus %1 dan semua komponennya dari komputer ini?
id.UninstalledAll=%1 sudah dihapus dari komputer ini.
id.UninstallStatusLabel=Tunggu sebentar, %1 sedang dihapus dari komputer ini.
id.UninstallAppFullTitle=Menghapus %1
id.SetupAlreadyRunning=Pemasangan sedang berjalan.

[CustomMessages]
en.DesktopIcon=Create a &desktop icon
en.SendToIcon=Add to the File Explorer right-click "&Send to" menu
en.LaunchApp=Open {#AppName} now
en.AdditionalIcons=Shortcuts:
en.AppComment=Turn documents into clean Markdown text
en.NeedWebView2=Urai App needs the Microsoft Edge WebView2 Runtime to show its window, but it was not found on this computer.%n%nWebView2 is free from Microsoft and is usually already included in up-to-date Windows 10 and 11. Open the WebView2 download page now? Urai App will still be installed.
id.DesktopIcon=Buat ikon di &Desktop
id.SendToIcon=Tambahkan ke menu klik kanan "&Kirim ke" di File Explorer
id.LaunchApp=Buka {#AppName} sekarang
id.AdditionalIcons=Pintasan:
id.AppComment=Urai dokumen jadi teks Markdown yang rapi
id.NeedWebView2=Urai App butuh Microsoft Edge WebView2 Runtime untuk menampilkan jendelanya, tetapi komponen itu tidak ditemukan di komputer ini.%n%nWebView2 gratis dari Microsoft dan biasanya sudah ada di Windows 10 dan 11 yang diperbarui. Buka halaman unduhan WebView2 sekarang? Pemasangan Urai App tetap dilanjutkan.

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "sendto"; Description: "{cm:SendToIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Bersihkan file versi lama supaya pustaka yang sudah tidak dipakai tidak tertinggal.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Urai App\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "{cm:AppComment}"; AppUserModelID: "mahesarnol.UraiApp"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon; AppUserModelID: "mahesarnol.UraiApp"
Name: "{usersendto}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: sendto

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[Code]
function WebView2Installed(): Boolean;
var
  Version: String;
  Key: String;
begin
  Key := 'Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\' + Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\' + Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'Software\' + Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

{ Pemasangan pertama dalam bahasa Indonesia: aplikasi juga dibuka dalam bahasa Indonesia.
  Pengaturan yang sudah ada tidak pernah ditimpa; aplikasi membaca file yang hanya berisi sebagian kunci. }
procedure SetFirstRunLanguage();
var
  Dir: String;
begin
  if ActiveLanguage() <> 'id' then
    Exit;
  Dir := ExpandConstant('{userappdata}\UraiApp');
  if FileExists(Dir + '\settings.json') then
    Exit;
  if ForceDirectories(Dir) then
    SaveStringToFile(Dir + '\settings.json', '{"lang": "id"}', False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
begin
  if CurStep = ssPostInstall then
    SetFirstRunLanguage();
  if (CurStep = ssPostInstall) and (not WizardSilent()) and (not WebView2Installed()) then
  begin
    if MsgBox(CustomMessage('NeedWebView2'), mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://developer.microsoft.com/microsoft-edge/webview2/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;
