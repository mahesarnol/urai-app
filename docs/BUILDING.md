# Publishing to GitHub and building the installer

**English** · [Bahasa Indonesia](BUILDING.id.md)

This guide is for the repo owner. The Windows installer is built by GitHub Actions, so you don't need to install Python or any other tools on your own computer.

## 1. Create the repo and upload

1. Sign in to GitHub and press **New repository**. Suggested name: `urai-app`. Choose **Public** (Actions is free without limits for public repos). Don't tick README or license, because they are already here.
2. Upload the contents of this folder. The easiest way without commands: on the empty repo page, choose **uploading an existing file**, then drag in all files and folders (including the `.github` folder). If the `.github` folder is left out because it is hidden, create it by hand: **Add file › Create new file**, type `.github/workflows/build.yml`, and paste its contents.

   With Git:

   ```bash
   git init
   git add .
   git commit -m "Urai App 3.0.0"
   git branch -M main
   git remote add origin https://github.com/YOUR-NAME/urai-app.git
   git push -u origin main
   ```

3. Open the **Actions** tab. The **Build** workflow runs automatically (about 15–25 minutes). If asked, press **I understand my workflows, go ahead and enable them**.

## 2. Get the test build

Once the green check mark appears, open that workflow run and download `UraiApp-3.0.0-windows` under **Artifacts**. It contains:

- `UraiApp-3.0.0-Setup.exe`: the installer
- `UraiApp-3.0.0-portable.zip`: the no-install version
- `SHA256SUMS.txt`: file fingerprints to confirm that nobody has altered the files

Try this installer on your own computer before releasing it.

## 3. Official release

Create a version tag, then push it:

```bash
git tag v3.0.0
git push origin v3.0.0
```

Without Git: **Releases › Draft a new release › Choose a tag**, type `v3.0.0`, choose **Create new tag**, then **Publish release**. The Build workflow runs for that tag and attaches the installer to the release.

Release notes are taken from [RELEASE_NOTES.md](RELEASE_NOTES.md). For the next version, bump `version` in `pyproject.toml` and `__version__` in `src/urai/__init__.py`, add notes to `CHANGELOG.md` and `docs/RELEASE_NOTES.md`, then create a tag that matches the version (e.g. `v3.0.1`). The workflow fails if the tag and the version don't match.

## 4. Google Drive

Upload `UraiApp-3.0.0-Setup.exe` and `SHA256SUMS.txt` from the Releases page to a Google Drive folder, then share it with **Anyone with the link: Viewer** access. Google Drive sometimes shows a "can't scan this file for viruses" warning for large files; that is normal.

## 5. Before a public release

- **QRIS**: the support QR code is `src/urai/web/img/qris.png` (the QR square only, with a white margin). To replace it, crop just the QR square from the new GoPay Merchant poster, and set `SUPPORT_MERCHANT` in `src/urai/info.py` to the merchant name encoded in the QR (that is the name payment apps show, and QRIS cuts it to 25 characters, so it can differ from the poster). Without the image, the Support window shows a "coming soon" placeholder.
- **Terms of Use and Privacy Policy**: drafts are in [TERMS.md](TERMS.md) and [PRIVACY.md](PRIVACY.md) (with Indonesian versions). Review them, decide the items marked **[to decide]**, then link them from the README.
- **Icon**: `packaging/urai.ico` is still a temporary plain icon (the letter U). Replace it with a logo once the name is safely registered.
- **SmartScreen warning**: an unsigned installer shows the "Windows protected your PC" warning until enough people have downloaded it. Removing it requires a (paid) code signing certificate. For open-source projects, [SignPath Foundation](https://signpath.org) offers free signing.

## Building on your own computer (optional)

On Windows 10/11 with Python 3.12, Inno Setup 6, and Tesseract (from Chocolatey or the UB Mannheim installer):

```powershell
pip install -r requirements-dev.txt
python packaging\write_build_info.py
.\packaging\fetch_tesseract.ps1 -Out build\tesseract
python packaging\gen_notices.py
pyinstaller packaging\urai.spec --noconfirm --clean
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" /DAppVersion=3.0.0 packaging\installer.iss
```

The output is in the `dist` folder. Headless self-test: `"dist\Urai App\Urai App.exe" --selftest build\selftest`, then check `build\selftest\selftest.json`.
