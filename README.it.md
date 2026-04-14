# Music Auto-Tagger

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

> **[Read in English](README.md)** | **[Sicurezza](SECURITY.it.md)**

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

> **Nota:** Il codice Python è cross-platform. L'installer automatico `install.sh` è specifico per Linux, ma sono disponibili guide passo passo per [macOS](#installazione-su-macos) e [Windows](#installazione-su-windows) più in basso.

## Installazione

### Setup Rapido (consigliato)

```bash
git clone https://github.com/AndreaBonn/audio-filename-fixer.git
cd audio-filename-fixer

# Installa tutto — richiede sudo per i pacchetti apt
bash install.sh /percorso/alla/tua/musica
```

L'installer fa tutto da solo:

- Installa le dipendenze di sistema (`ffmpeg`, `chromaprint-tools`)
- Installa [uv](https://docs.astral.sh/uv/) se non presente, poi sincronizza l'ambiente Python
- Crea `config.env` con la tua cartella musica
- Configura un servizio systemd con timer notturno (vedi [Schedulazione](#schedulazione))
- Esegue un test dry-run per verificare il setup

### Setup Manuale (Linux)

Se preferisci configurare tutto a mano su Linux:

```bash
cd audio-filename-fixer

# Installa dipendenze di sistema
sudo apt-get install -y ffmpeg chromaprint-tools

# Crea ambiente Python
uv sync

# Crea file di configurazione
cp .env.example config.env
# Modifica config.env con le tue impostazioni
```

### Installazione su macOS

<details>
<summary>Clicca per espandere la guida passo passo per macOS</summary>

#### Passo 1: Installa Homebrew (se non ce l'hai)

Homebrew è un gestore di pacchetti per macOS — pensalo come un "app store per strumenti da sviluppatore". Apri il **Terminale** (lo trovi in Applicazioni > Utility, oppure cercalo con Spotlight) e incolla:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Segui le istruzioni a schermo. Quando ha finito, chiudi e riapri il Terminale.

Per verificare che funzioni, scrivi:

```bash
brew --version
```

Dovresti vedere qualcosa come `Homebrew 4.x.x`.

#### Passo 2: Installa le dipendenze di sistema

Sempre nel Terminale, esegui:

```bash
brew install ffmpeg chromaprint
```

Questo installa `ffmpeg` (decodificatore audio) e `fpcalc` (strumento per il fingerprint audio). Potrebbe impiegare qualche minuto.

Verifica che siano installati:

```bash
ffmpeg -version
fpcalc -version
```

Entrambi i comandi dovrebbero stampare informazioni sulla versione (non "command not found").

#### Passo 3: Installa uv (gestore pacchetti Python)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Chiudi e riapri il Terminale, poi verifica:

```bash
uv --version
```

#### Passo 4: Scarica e configura il progetto

```bash
git clone https://github.com/AndreaBonn/audio-filename-fixer.git
cd audio-filename-fixer
uv sync
```

#### Passo 5: Crea il file di configurazione

```bash
cp .env.example config.env
```

Ora apri `config.env` con un qualsiasi editor di testo (TextEdit, VS Code, nano...) e imposta il percorso della tua cartella musica:

```bash
nano config.env
```

Modifica `MUSIC_DIR` in modo che punti alla tua cartella musica, ad esempio:

```
MUSIC_DIR=/Users/tuonome/Music
```

Salva e chiudi (in nano: `Ctrl+O`, `Invio`, `Ctrl+X`).

#### Passo 6: Testa il funzionamento

```bash
uv run python music_tagger.py --dry-run --music-dir ~/Music
```

Questo esegue in modalità anteprima — mostra cosa cambierebbe senza toccare nessun file. Se vedi un output che elenca i tuoi file audio, tutto funziona.

#### Passo 7: Esegui per davvero

Quando sei soddisfatto dell'output del dry-run:

```bash
uv run python music_tagger.py
```

#### Opzionale: Esecuzione automatica su macOS

macOS usa `launchd` invece di systemd. Per eseguire il tagger ogni notte alle 3:00:

1. Crea il file `~/Library/LaunchAgents/com.music-tagger.plist`:

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

2. Attivalo:

```bash
launchctl load ~/Library/LaunchAgents/com.music-tagger.plist
```

3. Per disattivarlo in futuro:

```bash
launchctl unload ~/Library/LaunchAgents/com.music-tagger.plist
```

</details>

### Installazione su Windows

<details>
<summary>Clicca per espandere la guida passo passo per Windows</summary>

#### Passo 1: Installa Python 3.11+

1. Vai su [python.org/downloads](https://www.python.org/downloads/) e scarica l'installer di Python più recente
2. Avvia l'installer
3. **Importante:** spunta la casella **"Add Python to PATH"** in fondo alla prima schermata
4. Clicca "Install Now"

Per verificare, apri **PowerShell** (cercalo nel menu Start) e scrivi:

```powershell
python --version
```

Dovresti vedere `Python 3.11.x` o superiore.

#### Passo 2: Installa Git (se non ce l'hai)

1. Vai su [git-scm.com/downloads/win](https://git-scm.com/downloads/win) e scarica l'installer
2. Avvialo con le impostazioni predefinite (clicca "Next" su tutte le schermate)

Verifica in PowerShell:

```powershell
git --version
```

#### Passo 3: Installa ffmpeg

1. Vai su [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) e scarica **"ffmpeg-release-essentials.zip"**
2. Estrai il file zip in `C:\ffmpeg` (crea questa cartella se non esiste)
3. All'interno troverai una cartella tipo `ffmpeg-7.x-essentials_build` — aprila e vai nella cartella `bin`
4. Copia il percorso completo della cartella `bin` (es. `C:\ffmpeg\ffmpeg-7.1-essentials_build\bin`)
5. Aggiungilo al PATH:
   - Premi `Win + R`, scrivi `sysdm.cpl`, premi Invio
   - Vai nella scheda **"Avanzate"**, clicca **"Variabili d'ambiente"**
   - In "Variabili utente", trova **"Path"**, selezionalo, clicca **"Modifica"**
   - Clicca **"Nuovo"** e incolla il percorso della cartella `bin`
   - Clicca **"OK"** su tutte le finestre

Chiudi e riapri PowerShell, poi verifica:

```powershell
ffmpeg -version
```

#### Passo 4: Installa fpcalc (Chromaprint)

1. Vai su [acoustid.org/chromaprint](https://acoustid.org/chromaprint) e scarica il pacchetto per **Windows**
2. Estrai il file zip
3. Copia `fpcalc.exe` nella stessa cartella `bin` dove hai messo ffmpeg (es. `C:\ffmpeg\ffmpeg-7.1-essentials_build\bin`), così è già nel tuo PATH

Verifica:

```powershell
fpcalc -version
```

#### Passo 5: Installa uv (gestore pacchetti Python)

In PowerShell, esegui:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Chiudi e riapri PowerShell, poi verifica:

```powershell
uv --version
```

#### Passo 6: Scarica e configura il progetto

```powershell
git clone https://github.com/AndreaBonn/audio-filename-fixer.git
cd audio-filename-fixer
uv sync
```

#### Passo 7: Crea il file di configurazione

```powershell
copy .env.example config.env
```

Apri `config.env` con il Blocco Note:

```powershell
notepad config.env
```

Modifica `MUSIC_DIR` in modo che punti alla tua cartella musica, ad esempio:

```
MUSIC_DIR=C:\Users\TuoNome\Music
```

Salva e chiudi il Blocco Note.

#### Passo 8: Carica la configurazione e testa

In PowerShell, devi caricare le variabili d'ambiente da `config.env` prima di eseguire:

```powershell
Get-Content config.env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}

uv run python music_tagger.py --dry-run
```

Questo esegue in modalità anteprima — mostra cosa cambierebbe senza toccare nessun file.

#### Passo 9: Esegui per davvero

Carica la configurazione ed esegui (stessi due comandi, senza `--dry-run`):

```powershell
Get-Content config.env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}

uv run python music_tagger.py
```

**Suggerimento:** Per evitare di digitare il comando di caricamento config ogni volta, puoi creare un file scorciatoia. Salva questo come `run.ps1` nella cartella del progetto:

```powershell
# run.ps1 — Esegui il music tagger su Windows
Get-Content "$PSScriptRoot\config.env" | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
    }
}
uv run python "$PSScriptRoot\music_tagger.py" @args
```

Poi eseguilo con: `powershell -File run.ps1` oppure `powershell -File run.ps1 --dry-run`.

#### Opzionale: Esecuzione automatica su Windows

1. Apri **Utilità di pianificazione** (cercalo nel menu Start)
2. Clicca **"Crea attività di base"** nel pannello destro
3. Nome: `Music Auto-Tagger`, clicca Avanti
4. Trigger: **Ogni giorno**, clicca Avanti
5. Imposta l'orario alle **3:00**, clicca Avanti
6. Azione: **Avvio programma**, clicca Avanti
7. Programma: `powershell`
8. Argomenti: `-ExecutionPolicy Bypass -File "C:\Users\TuoNome\audio-filename-fixer\run.ps1"`
9. Clicca Fine

Per testarlo subito: clicca col tasto destro sull'attività e seleziona **"Esegui"**.

</details>

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
audio-filename-fixer/
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
