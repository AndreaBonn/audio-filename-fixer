# Music Auto-Tagger

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

> **[Read in English](README.md)**

Corregge automaticamente i metadati e rinomina i file audio nella tua libreria musicale. Funziona ogni notte come servizio systemd o su richiesta da riga di comando.

## Cosa Fa

Per ogni file audio nella cartella musica (ricorsivamente):

1. **Salta se già processato** — tiene traccia dei file tramite checksum, le ri-esecuzioni sono veloci
2. **Fingerprint AcoustID** — identifica la canzone dalla forma d'onda audio (il metodo più accurato)
3. **Ricerca MusicBrainz** — cerca artista + titolo estratti dal nome file
4. **Fallback parser** — usa il nome file se non trova nulla online

Poi scrive i metadati corretti (titolo, artista, album, anno) e rinomina il file in `Artista-Titolo.ext`.

### Prima / Dopo

```
xXx_radiohead_creep_OFFICIAL_2023_[HD].mp3  -->  Radiohead-Creep.mp3
01 - unknown artist - no title.flac         -->  Radiohead-Creep.flac
some_random_hash_a8f3e2.ogg                 -->  Massive Attack-Teardrop.ogg
```

## Formati Supportati

MP3, FLAC, M4A, AAC, OGG, Opus, WMA

## Requisiti

- Linux (testato su Ubuntu/Xubuntu 22.04+)
- Python 3.11+
- `ffmpeg` e `chromaprint-tools` (installati automaticamente da `install.sh`)

## Installazione

### Setup Rapido (consigliato)

```bash
git clone <repo-url> music-tagger
cd music-tagger

# Installa tutto — richiede sudo per i pacchetti apt
bash install.sh /percorso/alla/tua/musica
```

L'installer fa tutto da solo:

- Installa le dipendenze di sistema (`ffmpeg`, `chromaprint-tools`)
- Installa [uv](https://docs.astral.sh/uv/) se non presente, poi sincronizza l'ambiente Python
- Crea `config.env` con la tua cartella musica
- Configura un servizio systemd con timer notturno (vedi [Schedulazione](#schedulazione))
- Esegue un test dry-run per verificare il setup

### Setup Manuale

Se preferisci configurare tutto a mano:

```bash
cd music-tagger

# Installa dipendenze di sistema
sudo apt-get install -y ffmpeg chromaprint-tools

# Crea ambiente Python
uv sync

# Crea file di configurazione
cp .env.example config.env
# Modifica config.env con le tue impostazioni
```

## Configurazione

Modifica `config.env` dopo l'installazione:

```env
MUSIC_DIR=/home/utente/Musica
ACOUSTID_API_KEY=la-tua-chiave
```

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `MUSIC_DIR` | Si | Percorso della cartella musica (scansionata ricorsivamente) |
| `ACOUSTID_API_KEY` | No | Chiave API AcoustID per il fingerprint audio |
| `STATE_FILE` | No | Percorso del file di stato (default: `state/processed.json`) |
| `LOG_FILE` | No | Percorso del file di log (default: `logs/tagger.log`) |

### Chiave API AcoustID (gratuita, consigliata)

AcoustID identifica le canzoni dalla forma d'onda audio — funziona anche quando il nome file è completamente sbagliato o privo di significato. Senza questa chiave, il tagger si basa solo sul parsing del nome file e sulla ricerca testuale su MusicBrainz.

1. Vai su [acoustid.org](https://acoustid.org/login) e crea un account gratuito
2. Registra una nuova applicazione
3. Copia la chiave API in `config.env`

## Utilizzo

### Comandi Base

```bash
# Dry run — anteprima delle modifiche senza toccare nessun file
bash run.sh --dry-run

# Esecuzione normale — correggi tag e rinomina file
bash run.sh

# Forza la ri-elaborazione di tutti i file (ignora lo stato)
bash run.sh --reset-state

# Elabora una cartella diversa (override temporaneo)
bash run.sh --music-dir /altro/percorso
```

### Cosa Succede Durante un'Esecuzione

1. Il tagger scansiona `MUSIC_DIR` ricorsivamente cercando file audio
2. I file già processati (tracciati tramite checksum SHA-1) vengono saltati
3. I file con tag completi e nome file corretto vengono segnati come completati
4. Per ogni file rimanente, prova la pipeline di ricerca a 3 livelli
5. In caso di successo: scrive i tag dei metadati e rinomina il file
6. In caso di fallimento: registra un warning e passa al file successivo
7. Lo stato viene salvato in `processed.json` per le esecuzioni future

### Dry Run

Esegui sempre con `--dry-run` la prima volta su una nuova cartella musica. Mostra esattamente cosa cambierebbe senza toccare nessun file:

```
2024-03-15 10:30:01 [INFO] → xXx_radiohead_creep_HD.mp3
2024-03-15 10:30:02 [INFO]   AcoustID match (score=0.95): Radiohead - Creep
2024-03-15 10:30:02 [INFO]   [DRY RUN] Tag: {'title': 'Creep', 'artists': ['Radiohead'], ...}
2024-03-15 10:30:02 [INFO]   [DRY RUN] Rinomina: xXx_radiohead_creep_HD.mp3 -> Radiohead-Creep.mp3
```

## Schedulazione

### Esecuzione Notturna Automatica (systemd)

Lo script `install.sh` configura un timer systemd utente che esegue il tagger ogni notte alle **03:00**. Se il PC era spento a quell'ora, parte appena riacceso (grazie a `Persistent=true`).

```bash
# Verifica stato del timer
systemctl --user status music-tagger.timer

# Visualizza prossima esecuzione programmata
systemctl --user list-timers music-tagger.timer

# Avvia manualmente il servizio
systemctl --user start music-tagger.service

# Disabilita le esecuzioni automatiche
systemctl --user disable --now music-tagger.timer

# Riabilita le esecuzioni automatiche
systemctl --user enable --now music-tagger.timer
```

### Schedulazione Manuale (cron)

Se preferisci cron a systemd:

```bash
# Modifica il tuo crontab
crontab -e

# Aggiungi questa riga per eseguire ogni notte alle 3:00
0 3 * * * cd /path/to/music-tagger && bash run.sh >> logs/cron.log 2>&1
```

## Struttura del Progetto

```
music-tagger/
├── music_tagger.py       # Entry point — orchestra la pipeline
├── src/
│   ├── config.py         # Configurazione centralizzata (dataclass + env vars)
│   ├── lookup.py         # Integrazione API AcoustID + MusicBrainz
│   ├── parser.py         # Parsing nomi file, slugify, split artisti
│   ├── state.py          # Tracking checksum + persistenza JSON atomica
│   └── tags.py           # Lettura/scrittura metadati audio (mutagen) + rinomina
├── tests/                # Specchia src/ — 65 test
│   ├── test_config.py
│   ├── test_lookup.py
│   ├── test_parser.py
│   ├── test_state.py
│   └── test_tags.py
├── install.sh            # Setup con un solo comando (deps + venv + systemd)
├── run.sh                # Wrapper per esecuzione manuale
├── config.env            # La tua configurazione (gitignored)
├── .env.example          # Template di configurazione
├── pyproject.toml        # Config progetto (uv, ruff, pytest)
├── logs/
│   └── tagger.log        # Tutte le operazioni vengono registrate qui
└── state/
    └── processed.json    # Traccia i file processati tramite checksum
```

## Come Funziona

### Pipeline di Ricerca

```
File Audio
    │
    ├─→ AcoustID (fingerprint) ──→ dettagli recording MusicBrainz
    │         score >= 0.5
    │
    ├─→ Ricerca testuale MusicBrainz ──→ artista + titolo da nome file/tag
    │         score >= 70
    │
    └─→ Parser nome file (fallback) ──→ estrazione basata su regex
              pattern "Artista - Titolo"
```

### Parser dei Nomi File

Gestisce i pattern comuni da download YouTube, CD rippati e librerie disordinate:

| Input | Artista Estratto | Titolo Estratto |
|---|---|---|
| `Radiohead - Creep` | Radiohead | Creep |
| `Drake feat. Rihanna - Take Care` | Drake, Rihanna | Take Care |
| `Simon & Garfunkel - The Sound of Silence` | Simon & Garfunkel | The Sound of Silence |
| `01. Radiohead - Creep [Official Video]` | Radiohead | Creep |

Il parser gestisce intelligentemente le collaborazioni `feat.`/`ft.` preservando i nomi delle band con `&` (es. Simon & Garfunkel resta come un unico artista).

### Gestione dello Stato

- Ogni file processato viene tracciato tramite percorso e checksum SHA-1 (primi 64KB)
- Se un file viene modificato esternamente, il checksum cambia e viene ri-elaborato
- Lo stato viene scritto atomicamente (scrittura su `.tmp`, poi rename) per prevenire corruzione
- `--reset-state` azzera lo stato e ri-elabora tutto

## Risoluzione Problemi

| Problema | Soluzione |
|---|---|
| `fpcalc not found` | Installa chromaprint: `sudo apt-get install chromaprint-tools` |
| AcoustID non trova risultati | Verifica la chiave API in `config.env`. Il tool funziona anche senza (usa il fallback di ricerca testuale). |
| Errori di permesso | Assicurati di essere il proprietario dei file: `ls -la /percorso/musica` |
| Prima esecuzione lenta | Normale — MusicBrainz limita a ~1 richiesta/secondo. Le esecuzioni successive saltano i file già processati. |
| Metadati scritti sbagliati | Esegui `--reset-state` per ri-elaborare. Controlla `logs/tagger.log` per dettagli. |
| Timer non funzionante | Verifica: `systemctl --user status music-tagger.timer` e `loginctl show-user $USER \| grep Linger` |

## Sviluppo

```bash
# Esegui test
uv run pytest -v

# Lint
uv run ruff check .

# Formattazione
uv run ruff format .

# Audit sicurezza
uv run bandit -r src/
uv run pip-audit
```

## Supporto

Se trovi utile questo progetto, considera di lasciare una stella su GitHub — aiuta altri a scoprirlo e motiva lo sviluppo futuro.

## Licenza

Copyright 2025 Andrea Bonacci

Distribuito sotto licenza Apache License, Version 2.0. Vedi [LICENSE](LICENSE) per i dettagli.
