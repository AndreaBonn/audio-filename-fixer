# Security

> **[Leggi in italiano](SECURITY.it.md)** | **[Back to README](README.md)**

This document describes the security measures implemented in Music Auto-Tagger, what data it accesses, and what guarantees it provides. The goal is to give you full transparency about what this tool does on your machine.

## Overview

Music Auto-Tagger is a **local-only, offline-first** tool. It runs on your machine, modifies only files you point it to, and contacts external APIs only when needed for song identification. It does not collect, store, or transmit any personal data.

## What It Accesses

### On Your Machine

| Resource | Access type | Why |
|---|---|---|
| Audio files in `MUSIC_DIR` | Read + Write | Reads audio for fingerprinting, writes corrected metadata and renames files |
| `state/processed.json` | Read + Write | Tracks which files have already been processed |
| `logs/tagger.log` | Write (append) | Logs all operations for your review |
| `config.env` | Read | Loads your configuration (music directory, API key) |

**Nothing else is accessed.** The tool does not read files outside your configured music directory, does not access your browser data, does not scan your home folder, and does not open any network ports.

### External Services

| Service | When contacted | What is sent | Why |
|---|---|---|---|
| [AcoustID](https://acoustid.org) | Only if `ACOUSTID_API_KEY` is set | Audio fingerprint (a numeric hash, not the audio itself) + your API key | Identifies the song from its audio waveform |
| [MusicBrainz](https://musicbrainz.org) | When AcoustID returns a match, or as text search fallback | Recording ID or artist+title search query | Retrieves correct metadata (title, artist, album, year) |

**No audio file content is ever uploaded.** AcoustID receives only a compact numeric fingerprint generated locally by `fpcalc` (Chromaprint). This fingerprint cannot be used to reconstruct the audio.

If you don't set `ACOUSTID_API_KEY`, the tool works entirely offline using filename parsing only — no network requests at all.

## Security Measures Implemented

### Filesystem Protection

- **Path traversal prevention**: before renaming any file, the new path is validated with `Path.resolve().is_relative_to()` to ensure it stays within the parent directory. A crafted filename like `../../etc/passwd` is blocked and logged as an error.

- **Filename sanitization**: all generated filenames pass through `slugify()`, which:
  - Normalizes Unicode to NFKC form (prevents homoglyph attacks)
  - Strips characters unsafe for filesystems (`< > : " / \ | ? *` and control characters `\x00-\x1f`)
  - Limits total filename length to 200 characters (prevents filesystem errors on ext4/NTFS)

- **Duplicate handling**: if the target filename already exists, a `_dup` suffix is appended instead of overwriting. Your existing files are never silently replaced.

- **Atomic state writes**: the state file is written to a `.tmp` file first, then atomically renamed. If the process crashes mid-write, the previous state file remains intact — no corruption.

### No Dangerous Patterns

| Pattern | Status | Detail |
|---|---|---|
| `eval()` / `exec()` | Not used | No dynamic code execution anywhere |
| `shell=True` in subprocess | Not used | `fpcalc` is called with argument list (`["fpcalc", "-version"]`), immune to shell injection |
| `pickle.loads()` | Not used | State is stored as plain JSON |
| Hardcoded credentials | None | API key is loaded from environment variable only |
| `SELECT *` / SQL | N/A | No database — state is a JSON file |

### Credential Management

- The `ACOUSTID_API_KEY` is loaded from `config.env` via environment variables, never hardcoded in source code
- `config.env` is listed in `.gitignore` — it is never committed to the repository
- `.env.example` is provided as a template with no real values
- The API key is only sent to the official AcoustID API endpoint over HTTPS

### Error Handling

The tool is designed to **never crash and never leave your files in a broken state**:

- Every file operation (`read`, `write`, `rename`) is wrapped in specific exception handlers (`PermissionError`, `OSError`)
- If a single file fails, the error is logged and the tool moves to the next file
- Permission errors are caught and reported without escalation — the tool never attempts `chmod` or `sudo`
- Corrupted state files are detected and the tool restarts with a clean state

### Rate Limiting

- MusicBrainz API calls are rate-limited to ~1 request per 1.2 seconds (respecting their usage policy)
- `fpcalc` availability is checked once and cached — no repeated subprocess spawning

### Dry Run Mode

Run with `--dry-run` to preview all changes without modifying a single file. This is the recommended first step on any new music library.

## What It Does NOT Do

- Does **not** run as root or request elevated privileges
- Does **not** open any network ports or start any server
- Does **not** install system-wide packages at runtime (only `install.sh` does, with explicit `sudo`)
- Does **not** execute any code from audio file metadata (tag content is treated as plain text)
- Does **not** download or execute remote code
- Does **not** send telemetry, analytics, or usage data to anyone
- Does **not** access files outside `MUSIC_DIR`

## Development Security

The project includes security tooling in its dev dependencies:

```bash
# Static security analysis (finds common vulnerability patterns)
uv run bandit -r src/

# Dependency vulnerability audit (checks for known CVEs)
uv run pip-audit
```

## Reporting a Vulnerability

If you find a security issue, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Contact the maintainer directly at [Andrea Bonacci's GitHub profile](https://github.com/AndreaBonn)
3. Include a description of the vulnerability and steps to reproduce
4. Allow reasonable time for a fix before public disclosure

## Summary

| Concern | Answer |
|---|---|
| Can it damage my files? | Only modifies metadata and filenames in your configured folder. Dry-run available. |
| Does it upload my music? | No. Only a numeric fingerprint is sent to AcoustID (if configured). |
| Does it collect personal data? | No. Zero telemetry, zero analytics. |
| Can a malicious filename exploit it? | No. Path traversal is blocked, filenames are sanitized. |
| Does it need internet? | Optional. Works offline with filename parsing only. |
| Does it run as root? | No. Runs as your user. |
