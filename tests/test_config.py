import os

import pytest

from src.config import Config


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
