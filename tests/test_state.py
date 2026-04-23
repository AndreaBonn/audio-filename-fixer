from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import Config
from src.state import already_processed, file_checksum, load_state, save_state


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    """Config con file temporanei per test isolati."""
    return Config(
        music_dir=str(tmp_path / "music"),
        state_file=str(tmp_path / "state" / "processed.json"),
        log_file=str(tmp_path / "logs" / "tagger.log"),
    )


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """File di test con contenuto noto."""
    f = tmp_path / "test.mp3"
    f.write_bytes(b"fake audio content for testing")
    return f


class TestFileChecksum:
    def test_returns_hex_string(self, sample_file: Path):
        result = file_checksum(str(sample_file))
        assert isinstance(result, str)
        assert len(result) == 40  # SHA-1 hex = 40 chars

    def test_same_content_same_checksum(self, tmp_path: Path):
        f1 = tmp_path / "a.mp3"
        f2 = tmp_path / "b.mp3"
        f1.write_bytes(b"same content")
        f2.write_bytes(b"same content")
        assert file_checksum(str(f1)) == file_checksum(str(f2))

    def test_different_content_different_checksum(self, tmp_path: Path):
        f1 = tmp_path / "a.mp3"
        f2 = tmp_path / "b.mp3"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert file_checksum(str(f1)) != file_checksum(str(f2))


class TestAlreadyProcessed:
    def test_unknown_file_returns_false(self, sample_file: Path):
        assert already_processed(str(sample_file), {}) is False

    def test_processed_unchanged_returns_true(self, sample_file: Path):
        path = str(sample_file)
        checksum = file_checksum(path)
        state = {path: checksum}
        assert already_processed(path, state) is True

    def test_processed_but_modified_returns_false(self, sample_file: Path):
        path = str(sample_file)
        state = {path: "old_checksum_that_doesnt_match"}
        assert already_processed(path, state) is False


class TestLoadSaveState:
    def test_load_empty_returns_empty_dict(self, tmp_config: Config):
        assert load_state(tmp_config) == {}

    def test_save_then_load_roundtrip(self, tmp_config: Config):
        Path(tmp_config.state_file).parent.mkdir(parents=True, exist_ok=True)
        state = {"/path/to/song.mp3": "abc123"}
        save_state(state, tmp_config)
        loaded = load_state(tmp_config)
        assert loaded == state

    def test_save_skipped_in_dry_run(self, tmp_config: Config):
        tmp_config.dry_run = True
        Path(tmp_config.state_file).parent.mkdir(parents=True, exist_ok=True)
        save_state({"key": "val"}, tmp_config)
        assert not Path(tmp_config.state_file).exists()

    def test_load_corrupted_file_returns_empty(self, tmp_config: Config):
        Path(tmp_config.state_file).parent.mkdir(parents=True, exist_ok=True)
        Path(tmp_config.state_file).write_text("not json{{{")
        result = load_state(tmp_config)
        assert result == {}

    def test_save_handles_os_error_and_cleans_tmp(self, tmp_config: Config):
        Path(tmp_config.state_file).parent.mkdir(parents=True, exist_ok=True)
        tmp_path = Path(tmp_config.state_file).with_suffix(".tmp")

        with patch("src.state.Path.write_text", side_effect=OSError("disk full")):
            save_state({"key": "val"}, tmp_config)

        assert not tmp_path.exists()
        assert not Path(tmp_config.state_file).exists()


class TestAlreadyProcessedExtra:
    def test_returns_false_when_file_unreadable(self, tmp_path: Path):
        path = str(tmp_path / "ghost.mp3")
        state = {path: "some_checksum"}
        with patch("src.state.file_checksum", side_effect=OSError("unreadable")):
            result = already_processed(path, state)
        assert result is False
