# Music Auto-Tagger

Rinomina e aggiusta i metadati delle canzoni automaticamente ogni giorno.

## Come funziona

Per ogni file audio nella cartella musica (e sottocartelle):

1. **Controlla se già processato** — salta i file già sistemati
2. **AcoustID fingerprint** — identifica la canzone dall'audio (il più accurato)
3. **MusicBrainz search** — cerca per artista+titolo estratti dal nome file
4. **Fallback parser** — usa il nome file se nulla trovato online

Alla fine rinomina il file come `Artista-Titolo.mp3` e aggiorna i metadati
(titolo, artista, album, anno).

## Installazione

```bash
# Clona o copia la cartella music-tagger sul tuo PC
cd music-tagger

# Installa tutto (richiede sudo per apt-get)
bash install.sh /percorso/alla/tua/musica
```

L'installer fa tutto da solo:
- Installa le dipendenze (`python3-venv`, `ffmpeg`, `chromaprint-tools`)
- Crea un ambiente virtuale Python con le librerie necessarie
- Crea un servizio systemd che si avvia ogni notte alle **03:00**
- Se il PC era spento, parte appena riacceso (grazie a `Persistent=true`)

## Configurazione

Modifica `config.env` dopo l'installazione:

```env
MUSIC_DIR=/home/utente/Musica     # La tua cartella musica
ACOUSTID_API_KEY=la-tua-chiave    # Vedi sotto
```

### API Key AcoustID (gratis, consigliata)

AcoustID identifica la canzone dall'audio stesso — funziona anche con
file con nomi completamente sbagliati.

1. Vai su https://acoustid.org/login
2. Registrati (gratuito)
3. Crea una nuova applicazione
4. Copia la chiave in `config.env`

## Uso manuale

```bash
# Dry run — simula senza modificare nulla
bash run.sh --dry-run

# Esecuzione normale
bash run.sh

# Forza riprocessamento di tutti i file
bash run.sh --reset-state

# Cartella diversa (override temporaneo)
bash run.sh --music-dir /altro/percorso
```

## Comandi utili

```bash
# Stato del timer automatico
systemctl --user status music-tagger.timer

# Log in tempo reale
tail -f logs/tagger.log

# Avvia manualmente il servizio systemd
systemctl --user start music-tagger.service

# Disabilita il timer automatico
systemctl --user disable music-tagger.timer
```

## Formati supportati

MP3, FLAC, M4A/AAC, OGG, Opus, WMA

## Struttura file

```
music-tagger/
├── music_tagger.py   # Script principale
├── install.sh        # Installazione automatica
├── run.sh            # Avvio manuale
├── config.env        # Configurazione (creato da install.sh)
├── .venv/            # Ambiente Python (creato da install.sh)
├── logs/
│   └── tagger.log    # Log di tutte le operazioni
└── state/
    └── processed.json # File già processati (non riprocessare)
```

## Note

- Il file `state/processed.json` tiene traccia dei file già sistemati.
  Se un file viene modificato esternamente, viene riprocessato automaticamente.
- I file con tag già completi e nome nel formato corretto vengono saltati.
- In caso di errore su un file, lo script continua con il successivo.
- MusicBrainz limita le richieste a ~1 al secondo — su librerie grandi
  la prima esecuzione potrebbe richiedere qualche minuto.
