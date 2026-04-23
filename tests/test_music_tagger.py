from pathlib import Path
from unittest.mock import patch

import pytest

from music_tagger import process_file, scan_directory
from src.config import Config


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        music_dir=str(tmp_path / "music"),
        state_file=str(tmp_path / "state" / "processed.json"),
        log_file=str(tmp_path / "logs" / "tagger.log"),
        acoustid_api_key="fake-key",
    )


@pytest.fixture
def mp3_file(tmp_path: Path) -> Path:
    f = tmp_path / "track.mp3"
    f.write_bytes(b"fake audio")
    return f


class TestProcessFile:
    def test_skips_already_processed_file(self, mp3_file: Path, config: Config):
        with patch("music_tagger.already_processed", return_value=True):
            result = process_file(str(mp3_file), {}, config)
        assert result is False

    def test_skips_non_audio_extension(self, tmp_path: Path, config: Config):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_bytes(b"text")
        result = process_file(str(txt_file), {}, config)
        assert result is False

    def test_skips_when_tags_complete_and_name_ok(self, tmp_path: Path, config: Config):
        f = tmp_path / "Radiohead - Creep.mp3"
        f.write_bytes(b"fake audio")
        complete_tags = {
            "title": "Creep",
            "artists": ["Radiohead"],
            "album": "",
            "year": "",
            "track": "",
        }
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch("music_tagger.read_existing_tags", return_value=complete_tags),
            patch("music_tagger.tags_look_complete", return_value=True),
            patch("music_tagger.file_checksum", return_value="abc123"),
        ):
            state: dict = {}
            result = process_file(str(f), state, config)
        assert result is False
        assert str(f) in state

    def test_uses_acoustid_when_available(self, mp3_file: Path, config: Config):
        acoustid_info = {
            "title": "Creep",
            "artists": ["Radiohead"],
            "album": "Pablo Honey",
            "year": "1993",
        }
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=acoustid_info),
            patch("music_tagger.write_tags", return_value=True),
            patch("music_tagger.rename_file", return_value=str(mp3_file)),
            patch("music_tagger.file_checksum", return_value="abc123"),
        ):
            result = process_file(str(mp3_file), {}, config)
        assert result is True

    def test_falls_back_to_mb_search(self, mp3_file: Path, config: Config):
        mb_info = {
            "title": "Creep",
            "artists": ["Radiohead"],
            "album": "Pablo Honey",
            "year": "1993",
        }
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=None),
            patch("music_tagger.mb_search", return_value=mb_info),
            patch("music_tagger.write_tags", return_value=True),
            patch("music_tagger.rename_file", return_value=str(mp3_file)),
            patch("music_tagger.file_checksum", return_value="abc123"),
        ):
            result = process_file(str(mp3_file), {}, config)
        assert result is True

    def test_falls_back_to_filename_parser(self, tmp_path: Path, config: Config):
        f = tmp_path / "Radiohead - Creep.mp3"
        f.write_bytes(b"fake audio")
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=None),
            patch("music_tagger.mb_search", return_value=None),
            patch("music_tagger.write_tags", return_value=True),
            patch("music_tagger.rename_file", return_value=str(f)),
            patch("music_tagger.file_checksum", return_value="abc123"),
        ):
            result = process_file(str(f), {}, config)
        assert result is True

    def test_returns_false_when_no_info_found(self, tmp_path: Path, config: Config):
        f = tmp_path / "xk72hd9as.mp3"
        f.write_bytes(b"fake audio")
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=None),
            patch("music_tagger.mb_search", return_value=None),
            patch("music_tagger.parse_filename", return_value=([], "")),
        ):
            result = process_file(str(f), {}, config)
        assert result is False

    def test_returns_false_when_write_tags_fails(self, mp3_file: Path, config: Config):
        acoustid_info = {"title": "Creep", "artists": ["Radiohead"], "album": "", "year": ""}
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=acoustid_info),
            patch("music_tagger.write_tags", return_value=False),
        ):
            result = process_file(str(mp3_file), {}, config)
        assert result is False

    def test_updates_state_after_success(self, mp3_file: Path, config: Config):
        new_path = str(mp3_file.parent / "Radiohead-Creep.mp3")
        acoustid_info = {"title": "Creep", "artists": ["Radiohead"], "album": "", "year": ""}
        state: dict = {}
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=acoustid_info),
            patch("music_tagger.write_tags", return_value=True),
            patch("music_tagger.rename_file", return_value=new_path),
            patch("music_tagger.file_checksum", return_value="newchecksum"),
        ):
            result = process_file(str(mp3_file), state, config)

        assert result is True
        assert new_path in state
        assert state[new_path] == "newchecksum"
        assert str(mp3_file) not in state

    def test_still_returns_true_when_checksum_fails(self, mp3_file: Path, config: Config):
        acoustid_info = {"title": "Creep", "artists": ["Radiohead"], "album": "", "year": ""}
        new_path = str(mp3_file.parent / "Radiohead-Creep.mp3")
        state: dict = {}
        with (
            patch("music_tagger.already_processed", return_value=False),
            patch(
                "music_tagger.read_existing_tags",
                return_value={"title": "", "artists": [], "album": "", "year": "", "track": ""},
            ),
            patch("music_tagger.tags_look_complete", return_value=False),
            patch("music_tagger.acoustid_lookup", return_value=acoustid_info),
            patch("music_tagger.write_tags", return_value=True),
            patch("music_tagger.rename_file", return_value=new_path),
            patch("music_tagger.file_checksum", side_effect=OSError("disk error")),
        ):
            result = process_file(str(mp3_file), state, config)
        assert result is True
        assert new_path not in state


class TestScanDirectory:
    def test_counts_files_correctly(self, tmp_path: Path, config: Config):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        for name in ("a.mp3", "b.mp3", "c.flac"):
            (music_dir / name).write_bytes(b"fake")
        config.music_dir = str(music_dir)

        with patch("music_tagger.process_file", return_value=False):
            total, modified, errors = scan_directory({}, config)

        assert total == 3
        assert modified == 0
        assert errors == 0

    def test_counts_errors(self, tmp_path: Path, config: Config):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        (music_dir / "bad.mp3").write_bytes(b"fake")
        (music_dir / "ok.mp3").write_bytes(b"fake")
        config.music_dir = str(music_dir)

        call_count = 0

        def process_side_effect(path, state, cfg):
            nonlocal call_count
            call_count += 1
            if "bad" in path:
                raise RuntimeError("unexpected error")
            return True

        with patch("music_tagger.process_file", side_effect=process_side_effect):
            total, modified, errors = scan_directory({}, config)

        assert total == 2
        assert modified == 1
        assert errors == 1

    def test_ignores_non_audio_files(self, tmp_path: Path, config: Config):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        (music_dir / "cover.jpg").write_bytes(b"image")
        (music_dir / "notes.txt").write_bytes(b"text")
        (music_dir / "song.mp3").write_bytes(b"fake audio")
        config.music_dir = str(music_dir)

        with patch("music_tagger.process_file", return_value=False) as mock_process:
            total, modified, errors = scan_directory({}, config)

        assert total == 1
        assert mock_process.call_count == 1


class TestMain:
    def test_exits_when_music_dir_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        missing = str(tmp_path / "does_not_exist")
        monkeypatch.setattr("sys.argv", ["music_tagger", "--music-dir", missing])
        with (
            patch("music_tagger.setup_logging"),
            pytest.raises(SystemExit) as exc_info,
        ):
            from music_tagger import main

            main()
        assert exc_info.value.code == 1

    def test_runs_scan_and_saves_state(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        monkeypatch.setattr(
            "sys.argv",
            ["music_tagger", "--music-dir", str(music_dir), "--dry-run"],
        )
        with (
            patch("music_tagger.setup_logging"),
            patch("music_tagger.load_state", return_value={}),
            patch("music_tagger.scan_directory", return_value=(0, 0, 0)),
            patch("music_tagger.save_state") as mock_save,
        ):
            from music_tagger import main

            main()
        mock_save.assert_called_once()

    def test_reset_state_loads_empty_dict(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        music_dir = tmp_path / "music"
        music_dir.mkdir()
        monkeypatch.setattr(
            "sys.argv",
            ["music_tagger", "--music-dir", str(music_dir), "--reset-state"],
        )
        with (
            patch("music_tagger.setup_logging"),
            patch("music_tagger.load_state", return_value={"old": "data"}) as mock_load,
            patch("music_tagger.scan_directory", return_value=(0, 0, 0)),
            patch("music_tagger.save_state"),
        ):
            from music_tagger import main

            main()
        mock_load.assert_not_called()
