#!/bin/bash
# run.sh — Avvia manualmente il music-tagger
# Uso: bash run.sh [--dry-run] [--reset-state] [--music-dir /percorso]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
CONFIG_FILE="$SCRIPT_DIR/config.env"

# Carica configurazione
if [ -f "$CONFIG_FILE" ]; then
    set -a
    source "$CONFIG_FILE"
    set +a
else
    echo "⚠ config.env non trovato in $SCRIPT_DIR"
    echo "  Esegui prima: bash install.sh"
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo "⚠ Ambiente virtuale non trovato. Esegui prima: bash install.sh"
    exit 1
fi

echo "Avvio Music Auto-Tagger..."
exec "$VENV_PYTHON" "$SCRIPT_DIR/music_tagger.py" "$@"
