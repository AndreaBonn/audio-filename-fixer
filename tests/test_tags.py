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

    @patch("src.tags.MutagenFile")
    def test_truncates_year_from_full_date(self, mock_file):
        """Data '1993-02-22' → anno '1993' (primi 4 caratteri)."""
        mock_audio = MagicMock()
        mock_audio.get.side_effect = lambda key, default=None: {
            "title": ["Song"],
            "artist": ["Band"],
            "album": ["Album"],
            "date": ["1993-02-22"],
            "tracknumber": ["1"],
        }.get(key, default)
        mock_file.return_value = mock_audio
        result = read_existing_tags("/fake/path.mp3")
        assert result["year"] == "1993"

    @patch("src.tags.MutagenFile", return_value=None)
    def test_returns_default_when_mutagen_returns_none(self, _mock):
        result = read_existing_tags("/fake/path.xyz")
        assert result["title"] == ""
        assert result["artists"] == []

    @patch("src.tags.MutagenFile", side_effect=PermissionError("access denied"))
    def test_handles_permission_error(self, _mock):
        result = read_existing_tags("/fake/path.mp3")
        assert result["title"] == ""
        assert result["artists"] == []

    @patch("src.tags.MutagenFile", side_effect=OSError("I/O error"))
    def test_handles_os_error(self, _mock):
        result = read_existing_tags("/fake/path.mp3")
        assert result["title"] == ""
        assert result["artists"] == []


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

    def test_returns_false_on_write_error(self, tmp_path: Path):
        bad_path = str(tmp_path / "nonexistent" / "file.mp3")
        result = write_tags(
            bad_path,
            {"title": "X", "artists": ["Y"], "album": "", "year": ""},
        )
        assert result is False

    def test_returns_true_on_success(self, mp3_file: Path):
        result = write_tags(
            str(mp3_file),
            {"title": "Creep", "artists": ["Radiohead"], "album": "", "year": ""},
        )
        assert result is True

    def test_dry_run_returns_true(self, mp3_file: Path):
        result = write_tags(
            str(mp3_file),
            {"title": "X", "artists": ["Y"], "album": "", "year": ""},
            dry_run=True,
        )
        assert result is True

    @patch("src.tags.FLAC")
    def test_writes_flac_tags(self, mock_flac_cls, tmp_path: Path):
        mock_audio = MagicMock()
        mock_flac_cls.return_value = mock_audio
        path = str(tmp_path / "track.flac")

        result = write_tags(
            path,
            {
                "title": "Karma Police",
                "artists": ["Radiohead"],
                "album": "OK Computer",
                "year": "1997",
            },
        )

        assert result is True
        mock_audio.__setitem__.assert_any_call("title", "Karma Police")
        mock_audio.__setitem__.assert_any_call("artist", "Radiohead")
        mock_audio.__setitem__.assert_any_call("album", "OK Computer")
        mock_audio.__setitem__.assert_any_call("date", "1997")
        mock_audio.save.assert_called_once()

    @patch("src.tags.MP4")
    def test_writes_m4a_tags(self, mock_mp4_cls, tmp_path: Path):
        mock_audio = MagicMock()
        mock_mp4_cls.return_value = mock_audio
        path = str(tmp_path / "track.m4a")

        result = write_tags(
            path,
            {"title": "Creep", "artists": ["Radiohead"], "album": "Pablo Honey", "year": "1993"},
        )

        assert result is True
        mock_audio.__setitem__.assert_any_call("\xa9nam", "Creep")
        mock_audio.__setitem__.assert_any_call("\xa9ART", "Radiohead")
        mock_audio.__setitem__.assert_any_call("\xa9alb", "Pablo Honey")
        mock_audio.__setitem__.assert_any_call("\xa9day", "1993")
        mock_audio.save.assert_called_once()

    @patch("src.tags.OggVorbis")
    def test_writes_ogg_tags(self, mock_ogg_cls, tmp_path: Path):
        mock_audio = MagicMock()
        mock_ogg_cls.return_value = mock_audio
        path = str(tmp_path / "track.ogg")

        result = write_tags(
            path,
            {
                "title": "High and Dry",
                "artists": ["Radiohead"],
                "album": "The Bends",
                "year": "1995",
            },
        )

        assert result is True
        mock_audio.__setitem__.assert_any_call("title", "High and Dry")
        mock_audio.__setitem__.assert_any_call("artist", "Radiohead")
        mock_audio.__setitem__.assert_any_call("album", "The Bends")
        mock_audio.__setitem__.assert_any_call("date", "1995")
        mock_audio.save.assert_called_once()

    @patch("src.tags.MutagenFile", return_value=None)
    def test_fallback_format_returns_false_when_unsupported(self, _mock, tmp_path: Path):
        path = str(tmp_path / "track.wma")
        result = write_tags(path, {"title": "X", "artists": ["Y"], "album": "", "year": ""})
        assert result is False

    @patch("src.tags.MutagenFile")
    def test_fallback_format_writes_via_easy_tags(self, mock_mutagen_cls, tmp_path: Path):
        mock_audio = MagicMock()
        mock_mutagen_cls.return_value = mock_audio
        path = str(tmp_path / "track.wma")

        result = write_tags(
            path,
            {
                "title": "Fake Plastic Trees",
                "artists": ["Radiohead"],
                "album": "The Bends",
                "year": "1995",
            },
        )

        assert result is True
        mock_audio.__setitem__.assert_any_call("title", "Fake Plastic Trees")
        mock_audio.__setitem__.assert_any_call("artist", "Radiohead")
        mock_audio.save.assert_called_once()

    def test_writes_mp3_without_album_and_year(self, mp3_file: Path):
        info = {"title": "Creep", "artists": ["Radiohead"], "album": "", "year": ""}
        result = write_tags(str(mp3_file), info)

        assert result is True
        tags = ID3(str(mp3_file))
        assert str(tags["TIT2"]) == "Creep"
        assert "TALB" not in tags
        assert "TDRC" not in tags

    def test_writes_mp3_without_id3_header(self, mp3_file: Path):
        """MP3 senza header ID3 → ID3NoHeaderError → crea nuovo tag."""
        from mutagen.id3 import ID3NoHeaderError as ID3Err

        original_id3 = ID3

        call_count = 0

        def id3_side_effect(path=None, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and path is not None:
                raise ID3Err("no ID3 header")
            return original_id3()

        with patch("src.tags.ID3", side_effect=id3_side_effect):
            result = write_tags(
                str(mp3_file),
                {"title": "Creep", "artists": ["Radiohead"], "album": "", "year": ""},
            )
        assert result is True

    def test_writes_mp3_multiple_artists_joined(self, mp3_file: Path):
        """Artisti multipli separati da '; ' nel tag TPE1."""
        info = {"title": "Song", "artists": ["A", "B", "C"], "album": "", "year": ""}
        write_tags(str(mp3_file), info)
        tags = ID3(str(mp3_file))
        assert str(tags["TPE1"]) == "A; B; C"

    @patch("src.tags.MP4")
    def test_writes_aac_tags(self, mock_mp4_cls, tmp_path: Path):
        """Estensione .aac usa lo stesso branch di .m4a."""
        mock_audio = MagicMock()
        mock_mp4_cls.return_value = mock_audio
        path = str(tmp_path / "track.aac")
        result = write_tags(
            path,
            {"title": "Song", "artists": ["Artist"], "album": "Album", "year": "2020"},
        )
        assert result is True
        mock_audio.__setitem__.assert_any_call("\xa9nam", "Song")
        mock_audio.__setitem__.assert_any_call("\xa9ART", "Artist")
        mock_audio.save.assert_called_once()

    @patch("src.tags.OggVorbis")
    def test_writes_opus_tags(self, mock_ogg_cls, tmp_path: Path):
        """Estensione .opus usa lo stesso branch di .ogg."""
        mock_audio = MagicMock()
        mock_ogg_cls.return_value = mock_audio
        path = str(tmp_path / "track.opus")
        result = write_tags(
            path,
            {"title": "Song", "artists": ["Artist"], "album": "Album", "year": "2020"},
        )
        assert result is True
        mock_audio.__setitem__.assert_any_call("title", "Song")
        mock_audio.__setitem__.assert_any_call("artist", "Artist")
        mock_audio.save.assert_called_once()

    @patch("src.tags.ID3", side_effect=PermissionError("access denied"))
    def test_handles_permission_error(self, _mock, mp3_file: Path):
        result = write_tags(
            str(mp3_file), {"title": "X", "artists": ["Y"], "album": "", "year": ""}
        )
        assert result is False

    @patch("src.tags.ID3", side_effect=OSError("I/O error"))
    def test_handles_os_error(self, _mock, mp3_file: Path):
        result = write_tags(
            str(mp3_file), {"title": "X", "artists": ["Y"], "album": "", "year": ""}
        )
        assert result is False


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

    def test_duplicate_file_preserves_content(self, tmp_path: Path):
        """Il file rinominato con _dup mantiene il contenuto originale."""
        existing = tmp_path / "Radiohead-Creep.mp3"
        existing.write_bytes(b"original content")
        f = tmp_path / "old_name.mp3"
        f.write_bytes(b"my content here")

        info = {"title": "Creep", "artists": ["Radiohead"]}
        new_path = rename_file(str(f), info)
        assert Path(new_path).read_bytes() == b"my content here"
        assert existing.read_bytes() == b"original content"

    def test_no_rename_if_already_correct(self, tmp_path: Path):
        f = tmp_path / "Radiohead-Creep.mp3"
        f.write_bytes(b"fake")
        info = {"title": "Creep", "artists": ["Radiohead"]}
        result = rename_file(str(f), info)
        assert result == str(f)

    def test_blocks_path_traversal(self, tmp_path: Path):
        f = tmp_path / "track.mp3"
        f.write_bytes(b"fake")
        # build_filename sanitizes input, so we mock it to force a traversal attempt
        with patch("src.tags.build_filename", return_value="../evil.mp3"):
            result = rename_file(str(f), {"title": "evil", "artists": ["../hack"]})
        assert result == str(f)
        assert f.exists()

    def test_handles_permission_error_on_rename(self, tmp_path: Path):
        f = tmp_path / "old_name.mp3"
        f.write_bytes(b"fake")
        info = {"title": "Creep", "artists": ["Radiohead"]}
        with patch("src.tags.Path.rename", side_effect=PermissionError("access denied")):
            result = rename_file(str(f), info)
        assert result == str(f)

    def test_handles_os_error_on_rename(self, tmp_path: Path):
        f = tmp_path / "old_name.mp3"
        f.write_bytes(b"fake")
        info = {"title": "Creep", "artists": ["Radiohead"]}
        with patch("src.tags.Path.rename", side_effect=OSError("I/O error")):
            result = rename_file(str(f), info)
        assert result == str(f)
