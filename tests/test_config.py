import os
from pathlib import Path

import pytest

from src.config import Config, setup_logging


class TestConfig:
    def test_from_env_defaults(self):
        config = Config.from_env()
        assert config.music_dir.endswith("Musica")
        assert config.dry_run is False
        assert config.acoustid_api_key == os.environ.get("ACOUSTID_API_KEY", "")

    def test_from_env_respects_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MUSIC_DIR", "/custom/music")
        monkeypatch.setenv("ACOUSTID_API_KEY", "test-key-123")
        config = Config.from_env()
        assert config.music_dir == "/custom/music"
        assert config.acoustid_api_key == "test-key-123"

    def test_dry_run_is_mutable(self):
        config = Config()
        config.dry_run = True
        assert config.dry_run is True


class TestSetupLogging:
    def test_creates_log_directory(self, tmp_path: Path):
        log_dir = tmp_path / "subdir" / "logs"
        state_dir = tmp_path / "state"
        config = Config(
            log_file=str(log_dir / "tagger.log"),
            state_file=str(state_dir / "processed.json"),
        )
        setup_logging(config)
        assert log_dir.exists()

    def test_creates_state_directory(self, tmp_path: Path):
        log_dir = tmp_path / "logs"
        state_dir = tmp_path / "subdir" / "state"
        config = Config(
            log_file=str(log_dir / "tagger.log"),
            state_file=str(state_dir / "processed.json"),
        )
        setup_logging(config)
        assert state_dir.exists()
