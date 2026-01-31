# Building a Windows executable for getsupernovae

This repository contains a Python/Tkinter app (`getsupernovae.py`). Two build options are provided to produce a Windows executable (`getsupernovae.exe`) including locale files and fonts.

Option A — Native Windows build (recommended when you have a Windows machine)

1. Open PowerShell in the project root.
2. Run:

```powershell
./build_windows.ps1
```

This will create a virtualenv, install dependencies and PyInstaller, and produce a single-file executable under `dist\getsupernovae.exe`.

Option B — Cross-build from Linux using Docker

This uses the `cdrx/pyinstaller-windows` image which contains a Windows Python toolchain and PyInstaller.

1. Ensure Docker is installed and running.
2. From the project root run:

```bash
chmod +x build_windows.sh
./build_windows.sh
```

The produced Windows executable will be in `dist/getsupernovae.exe`.

Notes and troubleshooting

- The build includes the `locales` folder (compiled `.mo` files) and `fonts` folder by default and copies `sites.json` into the exe bundle — adjust `--add-data` in the scripts if you have additional assets.
- If the GUI doesn't show translations, ensure compiled `.mo` files exist under `locales/<lang>/LC_MESSAGES/getsupernovae.mo`.
- If your app uses additional data files (templates, icons), add them to the `--add-data` lists in the build scripts.
- On Windows, you can test the exe by running `dist\getsupernovae.exe`.

If you want, I can:
- Add a `pyinstaller` spec file tailored to include additional hidden imports or binary hooks
- Add an icon file and wire it into the build
- Run a quick dry-run to detect missing data files (I can attempt a Docker build here if you want me to run it)

