import hashlib
import json
from pathlib import Path

from src.config import Config, log


def load_state(config: Config) -> dict:
    """Carica il dizionario dei file già processati {filepath: checksum}."""
    if Path(config.state_file).exists():
        try:
            with open(config.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"State file corrotto, riparto da zero: {e}")
    return {}


def save_state(state: dict, config: Config) -> None:
    """Persiste lo stato su disco con scrittura atomica (skip in dry-run)."""
    if config.dry_run:
        return

    state_path = Path(config.state_file)
    tmp_path = state_path.with_suffix(".tmp")
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(state_path)
    except OSError as e:
        log.error(f"Impossibile salvare stato in {config.state_file}: {e}")
        # Pulizia file temporaneo se esiste
        tmp_path.unlink(missing_ok=True)


def file_checksum(path: str) -> str:
    """SHA-1 dei primi 64KB — abbastanza per rilevare modifiche, veloce."""
    h = hashlib.sha1(usedforsecurity=False)
    with open(path, "rb") as f:
        h.update(f.read(65536))
    return h.hexdigest()


def already_processed(path: str, state: dict) -> bool:
    """True se il file è già stato sistemato e non è cambiato."""
    key = str(path)
    if key not in state:
        return False
    try:
        return state[key] == file_checksum(path)
    except OSError as e:
        log.warning(f"Impossibile calcolare checksum per {path}, verrà riprocessato: {e}")
        return False
