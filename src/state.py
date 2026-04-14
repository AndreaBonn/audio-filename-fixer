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


def save_state(state: dict, config: Config):
    """Persiste lo stato su disco (skip in dry-run)."""
    if not config.dry_run:
        with open(config.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


def file_checksum(path: str) -> str:
    """SHA-1 dei primi 64KB — abbastanza per rilevare modifiche, veloce."""
    h = hashlib.sha1()
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
    except OSError:
        return False
