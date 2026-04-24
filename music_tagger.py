#!/usr/bin/env python3
"""
music_tagger.py — Entry point
Rinomina e aggiusta i metadati delle canzoni nella cartella configurata.

Pipeline per ogni file:
  1. Parser regex sul nome file
  2. AcoustID (fingerprint audio) → MusicBrainz
  3. MusicBrainz text search (fallback)
  4. Salta con warning se nulla trovato

Formati supportati: mp3, flac, m4a, ogg, opus, aac, wma
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from src.config import AUDIO_EXTENSIONS, Config, log, setup_logging
from src.lookup import acoustid_lookup, mb_search
from src.parser import parse_filename
from src.state import already_processed, file_checksum, load_state, save_state
from src.tags import read_existing_tags, rename_file, tags_look_complete, write_tags


def process_file(path: str, state: dict, config: Config) -> bool:
    """
    Processa un file audio:
    - Salta se già processato e non modificato
    - Salta se i tag sono già completi e il nome è già nel formato giusto
    - Altrimenti cerca info e aggiorna

    Ritorna True se il file è stato modificato.
    """
    p = Path(path)
    log.info(f"→ {p.name}")

    if already_processed(path, state):
        log.info("  Già processato, skip")
        return False

    ext = p.suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        return False

    existing = read_existing_tags(path)

    # Controlla se il nome file è già nel formato corretto
    # \b\d{6,}\b cattura solo sequenze di 6+ cifre (ID video/hash),
    # evitando falsi positivi su nomi come "Blink 182" o "U2"
    name_ok = re.match(r"^[\w].+ - .+\.\w+$", p.name, re.UNICODE) and not re.search(
        r"(youtube|youtu\.be|\bvideo\b|www\.|http|official|\b\d{6,}\b)",
        p.stem,
        re.I,
    )

    if tags_look_complete(existing) and name_ok:
        log.info("  Tag completi e nome ok, segno come processato")
        state[path] = file_checksum(path)
        return False

    # Parse del nome file una sola volta
    parsed_artists, parsed_title = parse_filename(p.stem)

    # 1. Prova AcoustID (fingerprint) — più accurato
    info = acoustid_lookup(path, config)

    # 2. Prova MusicBrainz text search
    if not info:
        hint_artists = parsed_artists or existing.get("artists", [])
        hint_title = parsed_title or existing.get("title", "")
        info = mb_search(hint_artists, hint_title)

    # 3. Fallback: usa solo il parser del nome file
    if not info:
        if parsed_title:
            log.warning("  Nessun match online, uso nome file come fallback")
            info = {
                "title": parsed_title,
                "artists": parsed_artists or existing.get("artists", ["Unknown Artist"]),
                "album": existing.get("album", ""),
                "year": existing.get("year", ""),
            }
        else:
            log.warning(f"  ✗ Impossibile determinare info per {p.name}, skip")
            return False

    tags_written = write_tags(path, info, dry_run=config.dry_run)
    if not tags_written:
        return False

    new_path = rename_file(path, info, dry_run=config.dry_run)

    # Aggiorna state con il nuovo path
    try:
        checksum = file_checksum(new_path)
        state.pop(path, None)
        state[new_path] = checksum
    except OSError as e:
        log.warning(f"  Impossibile aggiornare state per {new_path}: {e}")

    return True


def scan_directory(state: dict, config: Config) -> tuple[int, int, int]:
    """
    Scansiona ricorsivamente la cartella musica.
    Ritorna (totale, modificati, errori).
    """
    total = modified = errors = 0

    for root, dirs, files in os.walk(config.music_dir):
        dirs.sort()
        files.sort()

        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in AUDIO_EXTENSIONS:
                continue

            fpath = str(Path(root) / fname)
            total += 1

            try:
                changed = process_file(fpath, state, config)
                if changed:
                    modified += 1
            except Exception as e:
                errors += 1
                log.error(f"  ✗ Errore inatteso su {fname}: {e}")

    return total, modified, errors


def main():
    config = Config.from_env()

    parser = argparse.ArgumentParser(description="Auto-tagger musicale")
    parser.add_argument("--dry-run", action="store_true", help="Simula senza modificare file")
    parser.add_argument(
        "--music-dir",
        default=config.music_dir,
        help=f"Cartella musica (default: {config.music_dir})",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reimposta lo stato (riprocessa tutto)",
    )
    args = parser.parse_args()

    config.dry_run = args.dry_run
    config.music_dir = args.music_dir

    setup_logging(config)

    if not Path(config.music_dir).is_dir():
        log.error(f"Cartella non trovata: {config.music_dir}")
        sys.exit(1)

    log.info("=" * 60)
    log.info(
        f"Music Filename-Fixer & Auto-Tagger avviato — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    log.info(f"Cartella: {config.music_dir}")
    if config.dry_run:
        log.info("** DRY RUN — nessun file verrà modificato **")
    log.info("=" * 60)

    state = {} if args.reset_state else load_state(config)

    total, modified, errors = scan_directory(state, config)

    save_state(state, config)

    log.info("=" * 60)
    log.info(f"Completato: {total} file scansionati, {modified} modificati, {errors} errori")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
