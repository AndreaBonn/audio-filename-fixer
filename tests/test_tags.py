from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mutagen.id3 import ID3

from src.tags import read_existing_tags, rename_file, tags_look_complete, write_tags


@pytest.fixture
def mp3_file(tmp_path: Path) -> Path:
    """Crea un MP3 minimale valido con header ID3 per i test."""
    # MP3 frame header minimo (sync word + valid header)
    # Usiamo mutagen per creare un file con tag validi
    f = tmp_path / "test.mp3"
    # Frame sync (0xFFE0) + layer III + 128kbps + 44100Hz + stereo
    # Minimo: ID3 header vuoto + un frame MP3 finto
    mp3_frame = (
        b"\xff\xfb\x90\x00"  # MPEG1 Layer3 128kbps 44100Hz stereo
        + b"\x00" * 417  # padding per un frame completo
    )
    f.write_bytes(mp3_frame * 3)  # qualche frame per mutagen
    return f


class TestReadExistingTags:
    def test_returns_default_for_untagged_file(self, mp3_file: Path):
        result = read_existing_tags(str(mp3_file))
        assert isinstance(result, dict)
        assert "title" in result
        assert "artists" in result

    def test_returns_default_for_nonexistent_file(self, tmp_path: Path):
        result = read_existing_tags(str(tmp_path / "nonexistent.mp3"))
        assert result["title"] == ""
        assert result["artists"] == []

    @patch("src.tags.MutagenFile")
    def test_reads_existing_tags_from_audio(self, mock_file):
        mock_audio = MagicMock()
        mock_audio.get.side_effect = lambda key, default=None: {
            "title": ["Test Song"],
            "artist": ["Test Artist"],
            "album": ["Test Album"],
            "date": ["2023"],
            "tracknumber": ["3"],
        }.get(key, default)
        mock_file.return_value = mock_audio

        result = read_existing_tags("/fake/path.mp3")
        assert result["title"] == "Test Song"
        assert result["artists"] == ["Test Artist"]
        assert result["album"] == "Test Album"
        assert result["year"] == "2023"
        assert result["track"] == "3"


class TestTagsLookComplete:
    def test_complete_tags(self):
        tags = {"title": "Creep", "artists": ["Radiohead"]}
        assert tags_look_complete(tags) is True

    def test_missing_title(self):
        tags = {"title": "", "artists": ["Radiohead"]}
        assert tags_look_complete(tags) is False

    def test_missing_artists(self):
        tags = {"title": "Creep", "artists": []}
        assert tags_look_complete(tags) is False

    def test_empty_artist_strings(self):
        tags = {"title": "Creep", "artists": ["", "  "]}
        assert tags_look_complete(tags) is False

    def test_whitespace_only_title(self):
        tags = {"title": "   ", "artists": ["Radiohead"]}
        assert tags_look_complete(tags) is False


class TestWriteTags:
    def test_dry_run_does_not_modify(self, mp3_file: Path):
        original_bytes = mp3_file.read_bytes()
        write_tags(
            str(mp3_file),
            {"title": "New", "artists": ["New Artist"], "album": "", "year": ""},
            dry_run=True,
        )
        assert mp3_file.read_bytes() == original_bytes

    def test_writes_mp3_tags(self, mp3_file: Path):
        info = {
            "title": "Creep",
            "artists": ["Radiohead"],
            "album": "Pablo Honey",
            "year": "1993",
        }
        write_tags(str(mp3_file), info)

        tags = ID3(str(mp3_file))
        assert str(tags["TIT2"]) == "Creep"
        assert "Radiohead" in str(tags["TPE1"])
        assert str(tags["TALB"]) == "Pablo Honey"

    def test_handles_write_error_gracefully(self, tmp_path: Path):
        bad_path = str(tmp_path / "nonexistent" / "file.mp3")
        # Non deve sollevare eccezioni
        write_tags(
            bad_path,
            {"title": "X", "artists": ["Y"], "album": "", "year": ""},
        )


class TestRenameFile:
    def test_renames_correctly(self, tmp_path: Path):
        f = tmp_path / "old_name.mp3"
        f.write_bytes(b"fake")
        info = {"title": "Creep", "artists": ["Radiohead"]}
        new_path = rename_file(str(f), info)
        assert Path(new_path).name == "Radiohead-Creep.mp3"
        assert Path(new_path).exists()
        assert not f.exists()

    def test_dry_run_does_not_rename(self, tmp_path: Path):
        f = tmp_path / "old_name.mp3"
        f.write_bytes(b"fake")
        info = {"title": "Creep", "artists": ["Radiohead"]}
        result = rename_file(str(f), info, dry_run=True)
        assert result == str(f)
        assert f.exists()

    def test_handles_duplicate_filename(self, tmp_path: Path):
        existing = tmp_path / "Radiohead-Creep.mp3"
        existing.write_bytes(b"original")
        f = tmp_path / "old_name.mp3"
        f.write_bytes(b"duplicate")

        info = {"title": "Creep", "artists": ["Radiohead"]}
        new_path = rename_file(str(f), info)
        assert Path(new_path).exists()
        assert existing.exists()  # originale intatto
        assert "_dup" in Path(new_path).stem

    def test_no_rename_if_already_correct(self, tmp_path: Path):
        f = tmp_path / "Radiohead-Creep.mp3"
        f.write_bytes(b"fake")
        info = {"title": "Creep", "artists": ["Radiohead"]}
        result = rename_file(str(f), info)
        assert result == str(f)
