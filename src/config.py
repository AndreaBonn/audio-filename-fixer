import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".aac", ".wma"}
REQUEST_DELAY = 1.2  # secondi tra chiamate API (rate limiting cortese)

_SCRIPT_DIR = Path(__file__).parent.parent

log = logging.getLogger("music_tagger")


@dataclass
class Config:
    """Configurazione centralizzata — niente più variabili globali mutabili."""

    music_dir: str = ""
    state_file: str = ""
    log_file: str = ""
    acoustid_api_key: str = ""
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            music_dir=os.environ.get("MUSIC_DIR", str(Path.home() / "Musica")),
            state_file=os.environ.get("STATE_FILE", str(_SCRIPT_DIR / "state" / "processed.json")),
            log_file=os.environ.get("LOG_FILE", str(_SCRIPT_DIR / "logs" / "tagger.log")),
            acoustid_api_key=os.environ.get("ACOUSTID_API_KEY", ""),
        )


def setup_logging(config: Config) -> None:
    """Configura logging su file e stdout."""
    Path(config.log_file).parent.mkdir(parents=True, exist_ok=True)
    Path(config.state_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(config.log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
