#!/bin/bash
# install.sh — Setup completo del music-tagger su Xubuntu
# Uso: bash install.sh [/percorso/alla/musica]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUSIC_DIR="${1:-$HOME/Musica}"
SERVICE_USER="$USER"
VENV_DIR="$SCRIPT_DIR/.venv"
LOG_DIR="$SCRIPT_DIR/logs"
STATE_DIR="$SCRIPT_DIR/state"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "======================================================"
echo "  Music Auto-Tagger — Installazione"
echo "======================================================"
echo "  Cartella musica : $MUSIC_DIR"
echo "  Script dir      : $SCRIPT_DIR"
echo "  Utente          : $SERVICE_USER"
echo "======================================================"
echo ""

# ── 1. Dipendenze di sistema ───────────────────────────────────────────────────
echo "[1/6] Installazione dipendenze di sistema..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    chromaprint-tools   `# fpcalc per AcoustID fingerprint` \
    ffmpeg              `# decodifica audio` \
    2>/dev/null

echo "  ✓ Dipendenze di sistema installate"

# ── 2. Ambiente virtuale Python (uv) ─────────────────────────────────────────
echo "[2/6] Creazione ambiente virtuale Python..."
if ! command -v uv &> /dev/null; then
    echo "  Installazione uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

cd "$SCRIPT_DIR"
uv sync

echo "  ✓ Ambiente virtuale creato in $VENV_DIR"

# ── 3. Directory e permessi ────────────────────────────────────────────────────
echo "[3/6] Creazione directory..."
mkdir -p "$LOG_DIR" "$STATE_DIR"
chmod 750 "$LOG_DIR" "$STATE_DIR"
echo "  ✓ Directory create"

# ── 4. File di configurazione ──────────────────────────────────────────────────
echo "[4/6] Creazione file di configurazione..."
cat > "$SCRIPT_DIR/config.env" << EOF
# Configurazione Music Auto-Tagger
# Modifica questo file secondo le tue esigenze

# Cartella contenente la musica (obbligatorio)
MUSIC_DIR=$MUSIC_DIR

# File di stato (tiene traccia dei file già processati)
STATE_FILE=$STATE_DIR/processed.json

# File di log
LOG_FILE=$LOG_DIR/tagger.log

# API Key di AcoustID (gratuita su https://acoustid.org/login)
# Registrati, crea un'applicazione e incolla qui la chiave
# Se lasci vuoto, il fingerprint audio verrà saltato (meno accurato)
ACOUSTID_API_KEY=

EOF
echo "  ✓ config.env creato"

# ── 5. Systemd user service (autostart dopo reboot) ───────────────────────────
echo "[5/6] Creazione servizio systemd..."
mkdir -p "$SYSTEMD_USER_DIR"

# Servizio principale
cat > "$SYSTEMD_USER_DIR/music-tagger.service" << EOF
[Unit]
Description=Music Auto-Tagger
After=network.target

[Service]
Type=oneshot
EnvironmentFile=$SCRIPT_DIR/config.env
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/music_tagger.py
StandardOutput=append:$LOG_DIR/tagger.log
StandardError=append:$LOG_DIR/tagger.log
# Riprova fino a 3 volte in caso di errore
Restart=on-failure
RestartSec=60

[Install]
WantedBy=default.target
EOF

# Timer giornaliero (esegue il servizio ogni giorno alle 3:00)
cat > "$SYSTEMD_USER_DIR/music-tagger.timer" << EOF
[Unit]
Description=Music Auto-Tagger — esecuzione giornaliera
Requires=music-tagger.service

[Timer]
# Esegui ogni giorno alle 03:00
OnCalendar=*-*-* 03:00:00
# Se il PC era spento all'orario previsto, esegui appena riacceso
Persistent=true
# Piccolo delay casuale per non sovraccaricare all'avvio
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

# Abilita il servizio utente persistente (sopravvive ai reboot)
systemctl --user daemon-reload
systemctl --user enable music-tagger.timer
systemctl --user start  music-tagger.timer

# Abilita il linger utente (i servizi utente partono senza login grafico)
loginctl enable-linger "$SERVICE_USER" 2>/dev/null || true

echo "  ✓ Servizio systemd creato e abilitato"

# ── 6. Test rapido (dry run) ───────────────────────────────────────────────────
echo "[6/6] Test rapido (dry run)..."
if [ -d "$MUSIC_DIR" ]; then
    source "$SCRIPT_DIR/config.env" 2>/dev/null || true
    "$VENV_DIR/bin/python" "$SCRIPT_DIR/music_tagger.py" \
        --dry-run \
        --music-dir "$MUSIC_DIR" \
        2>&1 | head -30
    echo "  ✓ Test dry run completato"
else
    echo "  ⚠ Cartella $MUSIC_DIR non trovata — test saltato"
    echo "    Modifica MUSIC_DIR in config.env prima di avviare"
fi

# ── Riepilogo ─────────────────────────────────────────────────────────────────
echo ""
echo "======================================================"
echo "  Installazione completata!"
echo "======================================================"
echo ""
echo "  Prossimi passi:"
echo ""
echo "  1. (Consigliato) Registrati su https://acoustid.org/login"
echo "     e aggiungi la tua ACOUSTID_API_KEY in:"
echo "     $SCRIPT_DIR/config.env"
echo ""
echo "  2. Verifica la cartella musica in config.env:"
echo "     MUSIC_DIR=$MUSIC_DIR"
echo ""
echo "  3. Esegui un test:"
echo "     bash $SCRIPT_DIR/run.sh --dry-run"
echo ""
echo "  4. Avvia manualmente la prima volta:"
echo "     bash $SCRIPT_DIR/run.sh"
echo ""
echo "  Il tagger girerà automaticamente ogni notte alle 03:00."
echo "  Se il PC era spento, partirà appena riacceso."
echo ""
echo "  Log: $LOG_DIR/tagger.log"
echo "  Stato timer: systemctl --user status music-tagger.timer"
echo "======================================================"
