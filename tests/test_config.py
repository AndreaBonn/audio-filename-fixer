import logging
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


class TestFromEnvAllFields:
    def test_state_file_respects_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("STATE_FILE", "/custom/state.json")
        config = Config.from_env()
        assert config.state_file == "/custom/state.json"

    def test_log_file_respects_env_var(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LOG_FILE", "/custom/tagger.log")
        config = Config.from_env()
        assert config.log_file == "/custom/tagger.log"

    def test_state_file_default_contains_processed_json(self):
        config = Config.from_env()
        assert config.state_file.endswith(os.path.join("state", "processed.json"))

    def test_log_file_default_contains_tagger_log(self):
        config = Config.from_env()
        assert config.log_file.endswith(os.path.join("logs", "tagger.log"))


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

    def test_configures_file_handler(self, tmp_path: Path):

        config = Config(
            log_file=str(tmp_path / "logs" / "tagger.log"),
            state_file=str(tmp_path / "state" / "processed.json"),
        )
        # Reset root logger handlers to test fresh setup
        root = logging.getLogger()
        old_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            setup_logging(config)
            handler_types = [type(h).__name__ for h in root.handlers]
            assert "FileHandler" in handler_types
            assert "StreamHandler" in handler_types
        finally:
            # Cleanup: restore original handlers
            for h in root.handlers[:]:
                h.close()
                root.removeHandler(h)
            root.handlers = old_handlers
