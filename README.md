# Music Auto-Tagger

<div align="center">

[![CI](https://github.com/AndreaBonn/audio-filename-fixer/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/audio-filename-fixer/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/audio-filename-fixer/main/badges/test-badge.json)](https://github.com/AndreaBonn/audio-filename-fixer/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/audio-filename-fixer/main/badges/coverage-badge.json)](https://github.com/AndreaBonn/audio-filename-fixer/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Security Policy](https://img.shields.io/badge/security-policy-blueviolet.svg)](SECURITY.md)

</div>

> **[Leggi in italiano](README.it.md)** | **[Security](SECURITY.md)**

Automatically fix metadata and rename audio files in your music library. Runs nightly as a systemd service or on-demand from the command line.

## What It Does

For every audio file in your music folder (recursively):

1. **Skip if already processed** — tracks files by checksum, so re-runs are fast
2. **AcoustID fingerprint** — identifies the song from the audio waveform itself (most accurate)
3. **MusicBrainz search** — looks up artist + title extracted from the filename
4. **Filename parser fallback** — uses the filename if nothing is found online

Then it writes correct metadata (title, artist, album, year) and renames the file to `Artist-Title.ext`.

### Before / After

```
xXx_radiohead_creep_OFFICIAL_2023_[HD].mp3  -->  Radiohead-Creep.mp3
01 - unknown artist - no title.flac         -->  Radiohead-Creep.flac
some_random_hash_a8f3e2.ogg                 -->  Massive Attack-Teardrop.ogg
```

## Supported Formats

MP3, FLAC, M4A, AAC, OGG, Opus, WMA

## Requirements

- Linux (tested on Ubuntu/Xubuntu 22.04+)
- Python 3.11+
- `ffmpeg` and `chromaprint-tools` (installed automatically by `install.sh`)

> **Note:** The Python code is cross-platform. The automated `install.sh` is Linux-specific, but step-by-step guides for [macOS](#macos-installation) and [Windows](#windows-installation) are provided below.

## Installation

### Quick Setup (recommended)

```bash
git clone https://github.com/AndreaBonn/audio-filename-fixer.git
cd audio-filename-fixer

# Install everything — requires sudo for apt packages
bash install.sh /path/to/your/music
```

The installer handles everything:

- Installs system dependencies (`ffmpeg`, `chromaprint-tools`)
- Installs [uv](https://docs.astral.sh/uv/) if not present, then syncs the Python environment
- Creates `config.env` with your music directory
- Sets up a systemd user service with a nightly timer (see [Scheduling](#scheduling))
- Runs a dry-run test to verify the setup

### Manual Setup (Linux)

If you prefer to set things up yourself on Linux:

```bash
cd audio-filename-fixer

# Install system dependencies
sudo apt-get install -y ffmpeg chromaprint-tools

# Create Python environment
uv sync

# Create config file
cp .env.example config.env
# Edit config.env with your settings
```

### macOS Installation

<details>
<summary>Click to expand the macOS step-by-step guide</summary>

#### Step 1: Install Homebrew (if you don't have it)

Homebrew is a package manager for macOS — think of it as an "app store for developer tools". Open **Terminal** (you can find it in Applications > Utilities, or search for it with Spotlight) and paste:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen instructions. When it finishes, close and reopen Terminal.

To verify it worked, type:

```bash
brew --version
```

You should see something like `Homebrew 4.x.x`.

#### Step 2: Install system dependencies

Still in Terminal, run:

```bash
brew install ffmpeg chromaprint
```

This installs `ffmpeg` (audio decoder) and `fpcalc` (audio fingerprinting tool). It may take a few minutes.

Verify both are installed:

```bash
ffmpeg -version
fpcalc -version
```

Both commands should print version information (not "command not found").

#### Step 3: Install uv (Python package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen Terminal, then verify:

```bash
uv --version
```

#### Step 4: Download and set up the project

```bash
git clone https://github.com/AndreaBonn/audio-filename-fixer.git
cd audio-filename-fixer
uv sync
```

#### Step 5: Create your configuration file

```bash
cp .env.example config.env
```

Now open `config.env` with any text editor (TextEdit, VS Code, nano...) and set your music folder path:

```bash
nano config.env
```

Change `MUSIC_DIR` to point to your music folder, for example:

```
MUSIC_DIR=/Users/yourname/Music
```

Save and close (in nano: `Ctrl+O`, `Enter`, `Ctrl+X`).

#### Step 6: Test it

```bash
uv run python music_tagger.py --dry-run --music-dir ~/Music
```

This runs in preview mode — it shows what would change without touching any file. If you see output listing your audio files, everything works.

#### Step 7: Run for real

When you're satisfied with the dry-run output:

```bash
uv run python music_tagger.py
```

#### Optional: Schedule automatic runs on macOS

macOS uses `launchd` instead of systemd. To run the tagger every night at 3:00 AM:

1. Create the file `~/Library/LaunchAgents/com.music-tagger.plist`:

```bash
mkdir -p ~/Library/LaunchAgents
cat > ~/Library/LaunchAgents/com.music-tagger.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.music-tagger</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd "$HOME/audio-filename-fixer" && source config.env && .venv/bin/python music_tagger.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/music-tagger.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/music-tagger.log</string>
</dict>
</plist>
EOF
```

2. Enable it:

```bash
launchctl load ~/Library/LaunchAgents/com.music-tagger.plist
```

3. To disable it later:

```bash
launchctl unload ~/Library/LaunchAgents/com.music-tagger.plist
```

</details>

### Windows Installation

<details>
<summary>Click to expand the Windows step-by-step guide</summary>

#### Step 1: Install Python 3.11+

1. Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest Python installer
2. Run the installer
3. **Important:** check the box **"Add Python to PATH"** at the bottom of the first screen
4. Click "Install Now"

To verify, open **PowerShell** (search for it in the Start menu) and type:

```powershell
python --version
```

You should see `Python 3.11.x` or higher.

#### Step 2: Install Git (if you don't have it)

1. Go to [git-scm.com/downloads/win](https://git-scm.com/downloads/win) and download the installer
2. Run it with default settings (click "Next" through all screens)

Verify in PowerShell:

```powershell
git --version
```

#### Step 3: Install ffmpeg

1. Go to [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and download **"ffmpeg-release-essentials.zip"**
2. Extract the zip file to `C:\ffmpeg` (create this folder if it doesn't exist)
3. Inside you'll find a folder like `ffmpeg-7.x-essentials_build` — open it and go into the `bin` folder
4. Copy the full path to the `bin` folder (e.g., `C:\ffmpeg\ffmpeg-7.1-essentials_build\bin`)
5. Add it to your PATH:
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Go to the **"Advanced"** tab, click **"Environment Variables"**
   - Under "User variables", find **"Path"**, select it, click **"Edit"**
   - Click **"New"** and paste the path to the `bin` folder
   - Click **"OK"** on all windows

Close and reopen PowerShell, then verify:

```powershell
ffmpeg -version
```

#### Step 4: Install fpcalc (Chromaprint)

1. Go to [acoustid.org/chromaprint](https://acoustid.org/chromaprint) and download the **Windows** package
2. Extract the zip file
3. Copy `fpcalc.exe` to the same `bin` folder where you put ffmpeg (e.g., `C:\ffmpeg\ffmpeg-7.1-essentials_build\bin`), so it's already in your PATH

Verify:

```powershell
fpcalc -version
```

#### Step 5: Install uv (Python package manager)

In PowerShell, run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell, then verify:

```powershell
uv --version
```

#### Step 6: Download and set up the project

```powershell
git clone https://github.com/AndreaBonn/audio-filename-fixer.git
cd audio-filename-fixer
uv sync
```

#### Step 7: Create your configuration file

```powershell
copy .env.example config.env
```

Open `config.env` with Notepad:

```powershell
notepad config.env
```

Change `MUSIC_DIR` to point to your music folder, for example:

```
MUSIC_DIR=C:\Users\YourName\Music
```

Save and close Notepad.

#### Step 8: Load the configuration and test

In PowerShell, you need to load the environment variables from `config.env` before running:

```powershell
Get-Content config.env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}

uv run python music_tagger.py --dry-run
```

This runs in preview mode — it shows what would change without touching any file.

#### Step 9: Run for real

Load the config and run (same two commands, without `--dry-run`):

```powershell
Get-Content config.env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}

uv run python music_tagger.py
```

**Tip:** To avoid typing the config loading command every time, you can create a shortcut file. Save this as `run.ps1` in the project folder:

```powershell
# run.ps1 — Run the music tagger on Windows
Get-Content "$PSScriptRoot\config.env" | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
uv run python "$PSScriptRoot\music_tagger.py" @args
```

Then run it with: `powershell -File run.ps1` or `powershell -File run.ps1 --dry-run`.

#### Optional: Schedule automatic runs on Windows

1. Open **Task Scheduler** (search for it in the Start menu)
2. Click **"Create Basic Task"** in the right panel
3. Name: `Music Auto-Tagger`, click Next
4. Trigger: **Daily**, click Next
5. Set the time to **3:00 AM**, click Next
6. Action: **Start a program**, click Next
7. Program: `powershell`
8. Arguments: `-ExecutionPolicy Bypass -File "C:\Users\YourName\audio-filename-fixer\run.ps1"`
9. Click Finish

To test it immediately: right-click the task and select **"Run"**.

</details>

## Configuration

Edit `config.env` after installation:

```env
MUSIC_DIR=/home/user/Music
ACOUSTID_API_KEY=your-key-here
```

| Variable | Required | Description |
|---|---|---|
| `MUSIC_DIR` | Yes | Path to your music folder (scanned recursively) |
| `ACOUSTID_API_KEY` | No | AcoustID API key for audio fingerprinting |
| `STATE_FILE` | No | Path to state file (default: `state/processed.json`) |
| `LOG_FILE` | No | Path to log file (default: `logs/tagger.log`) |

### AcoustID API Key (free, recommended)

AcoustID identifies songs from the audio waveform — it works even when the filename is completely wrong or meaningless. Without it, the tagger relies only on filename parsing and MusicBrainz text search.

1. Go to [acoustid.org](https://acoustid.org/login) and create a free account
2. Register a new application
3. Copy the API key into `config.env`

## Usage

### Basic Commands

```bash
# Dry run — preview changes without modifying any file
bash run.sh --dry-run

# Run normally — fix tags and rename files
bash run.sh

# Force reprocessing of all files (ignores state)
bash run.sh --reset-state

# Process a different folder (temporary override)
bash run.sh --music-dir /other/path
```

### What Happens During a Run

1. The tagger scans `MUSIC_DIR` recursively for audio files
2. Already-processed files (tracked by SHA-1 checksum) are skipped
3. Files with complete tags and a clean filename are marked as done
4. For each remaining file, it tries the 3-step lookup pipeline
5. On success: writes metadata tags and renames the file
6. On failure: logs a warning and moves to the next file
7. State is saved to `processed.json` for future runs

### Dry Run

Always run with `--dry-run` first on a new music folder. It shows exactly what would change without touching any file:

```
2024-03-15 10:30:01 [INFO] → xXx_radiohead_creep_HD.mp3
2024-03-15 10:30:02 [INFO]   AcoustID match (score=0.95): Radiohead - Creep
2024-03-15 10:30:02 [INFO]   [DRY RUN] Tag: {'title': 'Creep', 'artists': ['Radiohead'], ...}
2024-03-15 10:30:02 [INFO]   [DRY RUN] Rename: xXx_radiohead_creep_HD.mp3 -> Radiohead-Creep.mp3
```

## Scheduling

### Automatic Nightly Runs (systemd)

The `install.sh` script sets up a systemd user timer that runs the tagger every night at **03:00**. If the machine was off at that time, it runs as soon as it boots (thanks to `Persistent=true`).

```bash
# Check timer status
systemctl --user status music-tagger.timer

# View next scheduled run
systemctl --user list-timers music-tagger.timer

# Manually trigger the service
systemctl --user start music-tagger.service

# Disable automatic runs
systemctl --user disable --now music-tagger.timer

# Re-enable automatic runs
systemctl --user enable --now music-tagger.timer
```

### Manual Scheduling (cron)

If you prefer cron over systemd:

```bash
# Edit your crontab
crontab -e

# Add this line to run every night at 3:00 AM
0 3 * * * cd /path/to/music-tagger && bash run.sh >> logs/cron.log 2>&1
```

## Project Structure

```
audio-filename-fixer/
├── music_tagger.py       # Entry point — orchestrates the pipeline
├── src/
│   ├── config.py         # Centralized configuration (dataclass + env vars)
│   ├── lookup.py         # AcoustID + MusicBrainz API integration
│   ├── parser.py         # Filename parsing, slugify, artist splitting
│   ├── state.py          # Checksum tracking + atomic JSON persistence
│   └── tags.py           # Read/write audio metadata (mutagen) + rename
├── tests/                # Mirrors src/ — 65 tests
│   ├── test_config.py
│   ├── test_lookup.py
│   ├── test_parser.py
│   ├── test_state.py
│   └── test_tags.py
├── install.sh            # One-command setup (deps + venv + systemd)
├── run.sh                # Manual run wrapper
├── config.env            # Your configuration (gitignored)
├── .env.example          # Configuration template
├── pyproject.toml        # Project config (uv, ruff, pytest)
├── logs/
│   └── tagger.log        # All operations logged here
└── state/
    └── processed.json    # Tracks processed files by checksum
```

## How It Works

### Lookup Pipeline

```
Audio File
    │
    ├─→ AcoustID (fingerprint) ──→ MusicBrainz recording details
    │         score >= 0.5
    │
    ├─→ MusicBrainz text search ──→ artist + title from filename/tags
    │         score >= 70
    │
    └─→ Filename parser (fallback) ──→ regex-based extraction
              "Artist - Title" patterns
```

### Filename Parser

Handles common patterns from YouTube downloads, ripped CDs, and messy libraries:

| Input | Parsed Artist | Parsed Title |
|---|---|---|
| `Radiohead - Creep` | Radiohead | Creep |
| `Drake feat. Rihanna - Take Care` | Drake, Rihanna | Take Care |
| `Simon & Garfunkel - The Sound of Silence` | Simon & Garfunkel | The Sound of Silence |
| `01. Radiohead - Creep [Official Video]` | Radiohead | Creep |

The parser intelligently handles `feat.`/`ft.` collaborations while preserving band names with `&` (e.g., Simon & Garfunkel stays as one artist).

### State Management

- Each processed file is tracked by its path and a SHA-1 checksum (first 64KB)
- If a file is modified externally, the checksum changes and it gets reprocessed
- State is written atomically (write to `.tmp`, then rename) to prevent corruption
- `--reset-state` clears the state and reprocesses everything

## Troubleshooting

| Problem | Solution |
|---|---|
| `fpcalc not found` | Install chromaprint: `sudo apt-get install chromaprint-tools` |
| AcoustID not matching | Check your API key in `config.env`. The tool still works without it (text search fallback). |
| Permission errors | Ensure you own the music files: `ls -la /path/to/music` |
| Slow first run | Normal — MusicBrainz rate limits to ~1 request/second. Subsequent runs skip already-processed files. |
| Wrong metadata written | Run `--reset-state` to reprocess. Check `logs/tagger.log` for details. |
| Timer not running | Check: `systemctl --user status music-tagger.timer` and `loginctl show-user $USER \| grep Linger` |

## Development

```bash
# Run tests
uv run pytest -v

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Security audit
uv run bandit -r src/
uv run pip-audit
```

## Support

If you find this project useful, consider giving it a star on GitHub — it helps others discover it and motivates further development.

## License

Copyright 2025 Andrea Bonacci

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
