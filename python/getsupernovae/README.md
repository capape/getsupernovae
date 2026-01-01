# getSupernovae

A small scientific utility and GUI to fetch and inspect recent supernova (SN) reports from the Rochester listings, compute basic visibility for configured observing sites, and export results (PDF). This repository contains a Tkinter GUI front-end (`getsupernovae.py`) and a shell wrapper (`getsupernovae.sh`).

**Purpose**
- Download the most recent supernova list, parse entries, and filter by magnitude/date.
- Compute visibility windows for configured sites using Astropy.
- Provide a lightweight GUI to inspect and export results.

**Requirements**
- Python 3.8+ (3.11 recommended)
- See `requirements.txt` for the Python packages used by the project.

Typical dependencies (listed in `requirements.txt`):
- beautifulsoup4
- lxml
- astropy
- reportlab

Installation (recommended, inside a virtualenv):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app (GUI):

```bash
python getsupernovae.py
# or use the included shell wrapper (ensure it is executable)
./getsupernovae.sh
```

Usage (CLI / quick checks)
- Running the script without a display will fail because it opens a Tk GUI. Use a system with an X server or run with a virtual frame buffer (e.g. `xvfb`) for headless testing.

Configuration
- The application loads two user-editable configuration files from your user config directory:
  - `sites.json` — defines observing sites and their coordinates/metadata.
  - `old_supernovae.txt` — newline-separated list of previously-known / ignored SN names.

- On Linux these files live in: `~/.config/getsupernovae/`.
- On macOS or Windows the application uses platform-appropriate user config directories (the code falls back to package defaults if missing).

Bootstrapping
- On first run the app will copy package-default configuration files into your user config directory if they do not exist. The default site included is `Sabadell`.

Editing configuration
- To add or modify observing sites, edit `~/.config/getsupernovae/sites.json`.
- To ignore or mark SN as old, edit `~/.config/getsupernovae/old_supernovae.txt` (one name per line).

Examples
- Quick example to install deps and run the GUI:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python getsupernovae.py
```

Testing
- Unit tests are provided under `tests/` and use `pytest`.

```bash
# from the package directory
pip install -r requirements.txt
pip install pytest
pytest -q
```

Troubleshooting & Notes
- SSL: the current downloader uses the standard library; historically SSL verification was relaxed for some servers. If you see SSL errors, consider replacing the downloader with `requests` and enabling retries and proper certificate verification.
- GUI errors: if you get Tkinter callback errors, check that you are running the script with a supported Python version and that required packages are installed.
- If the app fails to find `sites.json` or `old_supernovae.txt`, it will create defaults in your user config directory. Inspect `~/.config/getsupernovae/` to see the generated files.

Contributing
- Bug reports and pull requests are welcome. Keep changes focused and add tests for parsing or visibility logic.

License
- This repository does not include a license file by default. Add a `LICENSE` if you want to share code with a specific license.

Contact
- For questions about usage or to request features, open an issue in the repository.
