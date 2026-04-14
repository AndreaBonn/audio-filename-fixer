# Music Auto-Tagger

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

> **[Leggi in italiano](README.it.md)**

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

## Installation

### Quick Setup (recommended)

```bash
git clone <repo-url> music-tagger
cd music-tagger

# Install everything — requires sudo for apt packages
bash install.sh /path/to/your/music
```

The installer handles everything:

- Installs system dependencies (`ffmpeg`, `chromaprint-tools`)
- Installs [uv](https://docs.astral.sh/uv/) if not present, then syncs the Python environment
- Creates `config.env` with your music directory
- Sets up a systemd user service with a nightly timer (see [Scheduling](#scheduling))
- Runs a dry-run test to verify the setup

### Manual Setup

If you prefer to set things up yourself:

```bash
cd music-tagger

# Install system dependencies
sudo apt-get install -y ffmpeg chromaprint-tools

# Create Python environment
uv sync

# Create config file
cp .env.example config.env
# Edit config.env with your settings
```

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
music-tagger/
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
