# Sicurezza

> **[Read in English](SECURITY.md)** | **[Torna al README](README.it.md)**

Questo documento descrive le misure di sicurezza implementate in Music Auto-Tagger, a quali dati accede e quali garanzie fornisce. L'obiettivo è darti piena trasparenza su cosa fa questo strumento sul tuo computer.

## Panoramica

Music Auto-Tagger è uno strumento **locale, offline-first**. Gira sulla tua macchina, modifica solo i file che gli indichi e contatta API esterne solo quando necessario per l'identificazione dei brani. Non raccoglie, memorizza o trasmette alcun dato personale.

## A Cosa Accede

### Sul Tuo Computer

| Risorsa | Tipo di accesso | Perché |
|---|---|---|
| File audio in `MUSIC_DIR` | Lettura + Scrittura | Legge l'audio per il fingerprinting, scrive i metadati corretti e rinomina i file |
| `state/processed.json` | Lettura + Scrittura | Tiene traccia dei file già processati |
| `logs/tagger.log` | Scrittura (append) | Registra tutte le operazioni per la tua revisione |
| `config.env` | Lettura | Carica la tua configurazione (cartella musica, chiave API) |

**Non accede a nient'altro.** Lo strumento non legge file fuori dalla cartella musica configurata, non accede ai dati del browser, non scansiona la home e non apre porte di rete.

### Servizi Esterni

| Servizio | Quando contattato | Cosa viene inviato | Perché |
|---|---|---|---|
| [AcoustID](https://acoustid.org) | Solo se `ACOUSTID_API_KEY` è impostata | Fingerprint audio (un hash numerico, non l'audio) + la tua chiave API | Identifica il brano dalla forma d'onda |
| [MusicBrainz](https://musicbrainz.org) | Quando AcoustID trova un match, o come ricerca testuale di fallback | ID del recording oppure query artista+titolo | Recupera i metadati corretti (titolo, artista, album, anno) |

**Nessun contenuto audio viene mai caricato.** AcoustID riceve solo un fingerprint numerico compatto generato localmente da `fpcalc` (Chromaprint). Questo fingerprint non può essere usato per ricostruire l'audio.

Se non imposti `ACOUSTID_API_KEY`, lo strumento funziona interamente offline usando solo il parsing del nome file — nessuna richiesta di rete.

## Misure di Sicurezza Implementate

### Protezione del Filesystem

- **Prevenzione path traversal**: prima di rinominare qualsiasi file, il nuovo percorso viene validato con `Path.resolve().is_relative_to()` per assicurare che rimanga nella directory padre. Un nome file come `../../etc/passwd` viene bloccato e registrato come errore.

- **Sanitizzazione nomi file**: tutti i nomi file generati passano attraverso `slugify()`, che:
  - Normalizza l'Unicode in forma NFKC (previene attacchi con omoglifi)
  - Rimuove i caratteri non sicuri per il filesystem (`< > : " / \ | ? *` e caratteri di controllo `\x00-\x1f`)
  - Limita la lunghezza totale del nome file a 200 caratteri (previene errori su ext4/NTFS)

- **Gestione duplicati**: se il nome file di destinazione esiste già, viene aggiunto un suffisso `_dup` invece di sovrascrivere. I tuoi file esistenti non vengono mai sostituiti silenziosamente.

- **Scrittura atomica dello stato**: il file di stato viene scritto prima in un file `.tmp`, poi rinominato atomicamente. Se il processo crasha durante la scrittura, il file di stato precedente resta intatto — nessuna corruzione.

### Nessun Pattern Pericoloso

| Pattern | Stato | Dettaglio |
|---|---|---|
| `eval()` / `exec()` | Non usato | Nessuna esecuzione dinamica di codice |
| `shell=True` in subprocess | Non usato | `fpcalc` viene chiamato con lista di argomenti (`["fpcalc", "-version"]`), immune a shell injection |
| `pickle.loads()` | Non usato | Lo stato è memorizzato come JSON puro |
| Credenziali hardcodate | Nessuna | La chiave API è caricata solo da variabile d'ambiente |
| `SELECT *` / SQL | N/A | Nessun database — lo stato è un file JSON |

### Gestione delle Credenziali

- La `ACOUSTID_API_KEY` è caricata da `config.env` tramite variabili d'ambiente, mai hardcodata nel codice sorgente
- `config.env` è nel `.gitignore` — non viene mai committato nel repository
- `.env.example` è fornito come template senza valori reali
- La chiave API viene inviata solo all'endpoint ufficiale AcoustID tramite HTTPS

### Gestione degli Errori

Lo strumento è progettato per **non crashare mai e non lasciare mai i tuoi file in uno stato corrotto**:

- Ogni operazione su file (`read`, `write`, `rename`) è incapsulata in handler specifici (`PermissionError`, `OSError`)
- Se un singolo file fallisce, l'errore viene registrato e lo strumento passa al file successivo
- Gli errori di permesso vengono catturati e riportati senza escalation — lo strumento non tenta mai `chmod` o `sudo`
- I file di stato corrotti vengono rilevati e lo strumento riparte con uno stato pulito

### Rate Limiting

- Le chiamate all'API MusicBrainz sono limitate a ~1 richiesta ogni 1.2 secondi (nel rispetto della loro policy d'uso)
- La disponibilità di `fpcalc` viene verificata una volta e cachata — nessuno spawn ripetuto di sottoprocessi

### Modalità Dry Run

Esegui con `--dry-run` per visualizzare tutte le modifiche senza toccare un singolo file. È il primo passo consigliato su qualsiasi nuova libreria musicale.

## Cosa NON Fa

- **Non** gira come root né richiede privilegi elevati
- **Non** apre porte di rete né avvia server
- **Non** installa pacchetti di sistema a runtime (solo `install.sh` lo fa, con `sudo` esplicito)
- **Non** esegue codice dai metadati dei file audio (il contenuto dei tag è trattato come testo semplice)
- **Non** scarica né esegue codice remoto
- **Non** invia telemetria, analytics o dati di utilizzo a nessuno
- **Non** accede a file fuori da `MUSIC_DIR`

## Sicurezza nello Sviluppo

Il progetto include strumenti di sicurezza nelle dipendenze di sviluppo:

```bash
# Analisi statica di sicurezza (trova pattern di vulnerabilità comuni)
uv run bandit -r src/

# Audit vulnerabilità dipendenze (verifica CVE note)
uv run pip-audit
```

## Segnalazione di Vulnerabilità

Se trovi un problema di sicurezza, segnalalo responsabilmente:

1. **Non** aprire una issue pubblica su GitHub
2. Contatta il maintainer direttamente sul [profilo GitHub di Andrea Bonacci](https://github.com/AndreaBonn)
3. Includi una descrizione della vulnerabilità e i passi per riprodurla
4. Concedi un tempo ragionevole per una fix prima della divulgazione pubblica

## Riepilogo

| Dubbio | Risposta |
|---|---|
| Può danneggiare i miei file? | Modifica solo metadati e nomi file nella cartella configurata. Dry-run disponibile. |
| Carica la mia musica? | No. Solo un fingerprint numerico viene inviato ad AcoustID (se configurato). |
| Raccoglie dati personali? | No. Zero telemetria, zero analytics. |
| Un nome file malevolo può sfruttarlo? | No. Il path traversal è bloccato, i nomi file sono sanitizzati. |
| Ha bisogno di internet? | Opzionale. Funziona offline con il solo parsing del nome file. |
| Gira come root? | No. Gira come il tuo utente. |
