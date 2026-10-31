; Installer Urai App (Inno Setup 6). Dirakit otomatis oleh GitHub Actions:
;   iscc /DAppVersion=3.0.0 packaging\installer.iss
; Dipasang per pengguna (tanpa hak admin) ke %LOCALAPPDATA%\Programs\Urai App ({autopf} pada mode per pengguna).
; Bila pengguna memilih "untuk semua pengguna" di awal, {autopf} menjadi Program Files.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Urai App"
#define AppExe "Urai App.exe"
#define AppPublisher "mahesarnol"

[Setup]
AppId={{6F2B7C0E-3D7A-4E3B-9A51-5B0E2C7D8A31}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppContact=maheswara.as@gmail.com
AppCopyright=(c) 2026 mahesarnol. Lisensi MIT.
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

[Languages]
Name: "id"; MessagesFile: "compiler:Default.isl"

; Inno Setup tidak menyertakan bahasa Indonesia resmi; pesan yang paling sering terlihat diterjemahkan di sini.
[Messages]
SetupAppTitle=Pemasangan
SetupWindowTitle=Pemasangan %1
ButtonBack=< &Kembali
ButtonNext=&Lanjut >
ButtonInstall=&Pasang
ButtonOK=OK
ButtonCancel=Batal
ButtonYes=&Ya
ButtonNo=&Tidak
ButtonFinish=&Selesai
ButtonBrowse=&Telusuri...
ButtonWizardBrowse=T&elusuri...
ExitSetupTitle=Keluar dari Pemasangan
ExitSetupMessage=Pemasangan belum selesai. Jika keluar sekarang, aplikasi tidak akan terpasang.%n%nKeluar dari Pemasangan?
WizardLicense=Perjanjian Lisensi
LicenseLabel=Bacalah informasi penting berikut sebelum melanjutkan.
LicenseLabel3=Urai App adalah perangkat lunak open source berlisensi MIT. Silakan baca lisensinya.
LicenseAccepted=Saya &menerima perjanjian ini
LicenseNotAccepted=Saya &tidak menerima perjanjian ini
WizardSelectDir=Pilih Lokasi Pemasangan
SelectDirDesc=Di mana [name] akan dipasang?
SelectDirLabel3=[name] akan dipasang ke folder berikut.
SelectDirBrowseLabel=Tekan Lanjut untuk meneruskan. Untuk memilih folder lain, tekan Telusuri.
WizardSelectTasks=Pilih Tugas Tambahan
SelectTasksDesc=Tugas tambahan apa yang perlu dilakukan?
SelectTasksLabel2=Pilih tugas tambahan yang diinginkan, lalu tekan Lanjut.
WizardReady=Siap Memasang
ReadyLabel1=[name] siap dipasang di komputer ini.
ReadyLabel2a=Tekan Pasang untuk mulai, atau Kembali untuk mengubah pilihan.
ReadyLabel2b=Tekan Pasang untuk mulai.
WizardPreparing=Menyiapkan Pemasangan
WizardInstalling=Memasang
InstallingLabel=Tunggu sebentar, [name] sedang dipasang di komputer ini.
FinishedHeadingLabel=Pemasangan [name] selesai
FinishedLabelNoIcons=[name] sudah terpasang di komputer ini.
FinishedLabel=[name] sudah terpasang. Buka lewat menu Start atau ikon yang dibuat.
ClickFinish=Tekan Selesai untuk menutup.
WelcomeLabel1=Selamat datang di Pemasangan [name]
WelcomeLabel2=[name/ver] akan dipasang di komputer ini.%n%nSebaiknya tutup aplikasi lain sebelum melanjutkan.
StatusExtractFiles=Menyalin file...
StatusCreateIcons=Membuat pintasan...
StatusUninstalling=Menghapus %1...
ConfirmUninstall=Hapus %1 dan semua komponennya dari komputer ini?
UninstalledAll=%1 sudah dihapus dari komputer ini.
UninstallStatusLabel=Tunggu sebentar, %1 sedang dihapus dari komputer ini.
UninstallAppFullTitle=Menghapus %1
SetupAlreadyRunning=Pemasangan sedang berjalan.

[CustomMessages]
DesktopIcon=Buat ikon di &Desktop
SendToIcon=Tambahkan ke menu klik kanan "&Kirim ke" di File Explorer
LaunchApp=Buka {#AppName} sekarang
AdditionalIcons=Pintasan:
NeedWebView2=Urai App butuh Microsoft Edge WebView2 Runtime untuk menampilkan jendelanya, tetapi komponen itu tidak ditemukan di komputer ini.%n%nWebView2 gratis dari Microsoft dan biasanya sudah ada di Windows 10 dan 11 yang diperbarui. Buka halaman unduhan WebView2 sekarang? Pemasangan Urai App tetap dilanjutkan.

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
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Urai dokumen jadi teks Markdown yang rapi"; AppUserModelID: "mahesarnol.UraiApp"
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

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
begin
  if (CurStep = ssPostInstall) and (not WizardSilent()) and (not WebView2Installed()) then
  begin
    if MsgBox(CustomMessage('NeedWebView2'), mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://developer.microsoft.com/microsoft-edge/webview2/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;
