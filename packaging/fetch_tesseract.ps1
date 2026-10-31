# Siapkan Tesseract OCR untuk dibundel ke installer: build\tesseract\
#   - tesseract.exe + DLL yang dibutuhkannya (dari build UB Mannheim)
#   - tessdata_fast 4.1.0 untuk ind, eng, jav, sun, ara, osd, dicek sha256-nya
# Dipakai GitHub Actions (windows-latest). Bisa juga dijalankan manual di Windows.
param(
    [string]$Out = "build\tesseract"
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$TessDir = Join-Path $env:ProgramFiles "Tesseract-OCR"
if (-not (Test-Path (Join-Path $TessDir "tesseract.exe"))) {
    Write-Host "Memasang Tesseract lewat Chocolatey..."
    choco install tesseract -y --no-progress
}
if (-not (Test-Path (Join-Path $TessDir "tesseract.exe"))) {
    Write-Host "Chocolatey gagal; mengunduh installer UB Mannheim dari GitHub Releases..."
    $tmp = Join-Path $env:RUNNER_TEMP "tess-setup"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    gh release download --repo UB-Mannheim/tesseract --pattern "*w64-setup*.exe" --dir $tmp --clobber
    $setup = Get-ChildItem $tmp -Filter "*w64-setup*.exe" | Select-Object -First 1
    Start-Process -FilePath $setup.FullName -ArgumentList "/S", "/D=$TessDir" -Wait
}
if (-not (Test-Path (Join-Path $TessDir "tesseract.exe"))) { throw "Tesseract tidak berhasil dipasang" }
& (Join-Path $TessDir "tesseract.exe") --version

if (Test-Path $Out) { Remove-Item -Recurse -Force $Out }
python packaging/tess_deps.py $TessDir $Out
if ($LASTEXITCODE -ne 0) { throw "Gagal menyalin Tesseract" }

# Data bahasa: tessdata_fast 4.1.0 (Apache 2.0). Versi "fast" kecil dan cepat untuk prosesor biasa.
$Tessdata = Join-Path $Out "tessdata"
New-Item -ItemType Directory -Force -Path $Tessdata | Out-Null
$Base = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0"
$Langs = [ordered]@{
    "ind" = "69786901da87ab8766c1ea7fbb10b28f2110c14da3f6c8f2735df131fba95d88"
    "eng" = "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2"
    "jav" = "46107b6bed3bf2d9617e5e192e52524e368242543fead1a7175c363dddd400f2"
    "sun" = "fa939213b005b3477a1032b7222f63cd0b0ac486f83fd9554caf653d6e6c6ffe"
    "ara" = "e3206d3dc87fd50c24a0fb9f01838615911d25168f4e64415244b67d2bb3e729"
    "osd" = "9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff"
}
foreach ($lang in $Langs.Keys) {
    $file = Join-Path $Tessdata "$lang.traineddata"
    Invoke-WebRequest -Uri "$Base/$lang.traineddata" -OutFile $file
    $hash = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $Langs[$lang]) { throw "sha256 $lang.traineddata tidak cocok: $hash" }
    Write-Host "  $lang.traineddata ok"
}
Invoke-WebRequest -Uri "$Base/LICENSE" -OutFile (Join-Path $Tessdata "LICENSE-tessdata.txt")
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/tesseract-ocr/tesseract/main/LICENSE" -OutFile (Join-Path $Out "LICENSE-tesseract.txt")

# Uji: bahasa terbaca dari folder bundel, dengan PATH bersih supaya DLL yang kurang langsung ketahuan
$oldPath = $env:PATH
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
$env:TESSDATA_PREFIX = (Resolve-Path $Tessdata).Path
& (Join-Path $Out "tesseract.exe") --list-langs
$code = $LASTEXITCODE
$env:PATH = $oldPath
Remove-Item Env:\TESSDATA_PREFIX
if ($code -ne 0) { throw "tesseract hasil salinan tidak bisa dijalankan (kode $code)" }
Write-Host "Tesseract siap di $Out"
