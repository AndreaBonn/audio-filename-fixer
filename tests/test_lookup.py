from unittest.mock import MagicMock, patch

import acoustid as acoustid_lib
import pytest
from musicbrainzngs import MusicBrainzError

from src.config import Config
from src.lookup import _fpcalc_available, _mb_recording_details, acoustid_lookup, mb_search


@pytest.fixture
def config_with_key() -> Config:
    return Config(acoustid_api_key="fake-key-123")


@pytest.fixture
def config_no_key() -> Config:
    return Config(acoustid_api_key="")


MB_RECORDING_RESPONSE = {
    "recording": {
        "title": "Creep",
        "artist-credit": [{"artist": {"name": "Radiohead"}}],
        "release-list": [{"title": "Pablo Honey", "date": "1993-02-22"}],
    }
}

MB_SEARCH_RESPONSE = {
    "recording-list": [
        {
            "ext:score": "95",
            "title": "Creep",
            "artist-credit": [{"artist": {"name": "Radiohead"}}],
            "release-list": [{"title": "Pablo Honey", "date": "1993-02-22"}],
        }
    ]
}


class TestFpcalcAvailable:
    def test_returns_false_when_fpcalc_missing(self):
        _fpcalc_available.cache_clear()
        with patch("src.lookup.subprocess.run", side_effect=FileNotFoundError):
            result = _fpcalc_available()
        _fpcalc_available.cache_clear()
        assert result is False

    def test_returns_true_when_fpcalc_present(self):
        _fpcalc_available.cache_clear()
        with patch("src.lookup.subprocess.run", return_value=MagicMock(returncode=0)):
            result = _fpcalc_available()
        _fpcalc_available.cache_clear()
        assert result is True


class TestAcoustidLookup:
    def test_returns_none_without_api_key(self, config_no_key: Config):
        result = acoustid_lookup("/fake/path.mp3", config_no_key)
        assert result is None

    @patch("src.lookup._fpcalc_available", return_value=False)
    def test_returns_none_without_fpcalc(self, _mock, config_with_key: Config):
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None

    @patch("src.lookup._mb_recording_details")
    @patch("src.lookup.acoustid.match")
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_returns_details_on_high_score(
        self, _fpcalc, mock_match, mock_details, config_with_key: Config
    ):
        mock_match.return_value = [(0.9, "rec-id-123", "Creep", "Radiohead")]
        mock_details.return_value = {
            "title": "Creep",
            "artists": ["Radiohead"],
            "album": "Pablo Honey",
            "year": "1993",
        }
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result["title"] == "Creep"
        assert result["artists"] == ["Radiohead"]
        mock_details.assert_called_once_with("rec-id-123")

    @patch("src.lookup.acoustid.match")
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_skips_low_score_results(self, _fpcalc, mock_match, config_with_key: Config):
        mock_match.return_value = [(0.2, "rec-id", "Wrong", "Wrong Artist")]
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None

    @patch(
        "src.lookup.acoustid.match",
        side_effect=acoustid_lib.WebServiceError("network error"),
    )
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_returns_none_on_api_error(self, _fpcalc, _mock_match, config_with_key: Config):
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None

    @patch(
        "src.lookup.acoustid.match",
        side_effect=acoustid_lib.FingerprintGenerationError("no fingerprint"),
    )
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_returns_none_on_fingerprint_error(self, _fpcalc, _mock_match, config_with_key: Config):
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None

    @patch(
        "src.lookup.acoustid.match",
        side_effect=acoustid_lib.AcoustidError("generic error"),
    )
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_returns_none_on_acoustid_error(self, _fpcalc, _mock_match, config_with_key: Config):
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None

    @patch("src.lookup.acoustid.match", side_effect=OSError("I/O error"))
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_returns_none_on_os_error(self, _fpcalc, _mock_match, config_with_key: Config):
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None

    @patch("src.lookup._mb_recording_details")
    @patch("src.lookup.acoustid.match")
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_accepts_score_exactly_0_5(
        self, _fpcalc, mock_match, mock_details, config_with_key: Config
    ):
        """Boundary: score == 0.5 è >= 0.5, deve essere accettato."""
        mock_match.return_value = [(0.5, "rec-id", "Title", "Artist")]
        mock_details.return_value = {
            "title": "Title",
            "artists": ["Artist"],
            "album": "",
            "year": "",
        }
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is not None
        assert result["title"] == "Title"
        mock_details.assert_called_once_with("rec-id")

    @patch("src.lookup.acoustid.match")
    @patch("src.lookup._fpcalc_available", return_value=True)
    def test_rejects_score_just_below_0_5(self, _fpcalc, mock_match, config_with_key: Config):
        """Boundary: score == 0.49 è < 0.5, deve essere rifiutato."""
        mock_match.return_value = [(0.49, "rec-id", "Title", "Artist")]
        result = acoustid_lookup("/fake/path.mp3", config_with_key)
        assert result is None


class TestMbRecordingDetails:
    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_extracts_all_fields(self, mock_get, _sleep):
        mock_get.return_value = MB_RECORDING_RESPONSE
        result = _mb_recording_details("rec-id-123")
        assert result == {
            "title": "Creep",
            "artists": ["Radiohead"],
            "album": "Pablo Honey",
            "year": "1993",
        }

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_returns_none_without_title(self, mock_get, _sleep):
        mock_get.return_value = {
            "recording": {
                "title": "",
                "artist-credit": [{"artist": {"name": "Radiohead"}}],
            }
        }
        assert _mb_recording_details("rec-id") is None

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_handles_no_releases(self, mock_get, _sleep):
        mock_get.return_value = {
            "recording": {
                "title": "Creep",
                "artist-credit": [{"artist": {"name": "Radiohead"}}],
                "release-list": [],
            }
        }
        result = _mb_recording_details("rec-id")
        assert result["album"] == ""
        assert result["year"] == ""

    @patch("src.lookup.time.sleep")
    @patch(
        "src.lookup.musicbrainzngs.get_recording_by_id",
        side_effect=MusicBrainzError("timeout"),
    )
    def test_returns_none_on_error(self, _mock_get, _sleep):
        assert _mb_recording_details("rec-id") is None

    @patch("src.lookup.time.sleep")
    @patch(
        "src.lookup.musicbrainzngs.get_recording_by_id",
        side_effect=OSError("network I/O error"),
    )
    def test_returns_none_on_os_error(self, _mock_get, _sleep):
        assert _mb_recording_details("rec-id") is None

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_filters_non_dict_artist_credit_entries(self, mock_get, _sleep):
        """MusicBrainz artist-credit può contenere stringhe join come ' & '."""
        mock_get.return_value = {
            "recording": {
                "title": "Under Pressure",
                "artist-credit": [
                    {"artist": {"name": "Queen"}},
                    " & ",
                    {"artist": {"name": "David Bowie"}},
                ],
                "release-list": [],
            }
        }
        result = _mb_recording_details("rec-id")
        assert result["artists"] == ["Queen", "David Bowie"]

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_handles_malformed_short_date(self, mock_get, _sleep):
        """Data con meno di 4 caratteri non causa errori."""
        mock_get.return_value = {
            "recording": {
                "title": "Song",
                "artist-credit": [{"artist": {"name": "Band"}}],
                "release-list": [{"title": "Album", "date": "199"}],
            }
        }
        result = _mb_recording_details("rec-id")
        assert result["year"] == "199"

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_truncates_full_date_to_four_chars(self, mock_get, _sleep):
        """Data completa '1993-02-22' → anno '1993'."""
        mock_get.return_value = {
            "recording": {
                "title": "Creep",
                "artist-credit": [{"artist": {"name": "Radiohead"}}],
                "release-list": [{"title": "Pablo Honey", "date": "1993-02-22"}],
            }
        }
        result = _mb_recording_details("rec-id")
        assert result["year"] == "1993"

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.get_recording_by_id")
    def test_returns_none_when_no_artists(self, mock_get, _sleep):
        mock_get.return_value = {
            "recording": {
                "title": "Song",
                "artist-credit": [],
                "release-list": [],
            }
        }
        assert _mb_recording_details("rec-id") is None


class TestMbSearch:
    def test_returns_none_with_no_input(self):
        assert mb_search(artists=[], title="") is None

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_returns_match_above_threshold(self, mock_search, _sleep):
        mock_search.return_value = MB_SEARCH_RESPONSE
        result = mb_search(artists=["Radiohead"], title="Creep")
        assert result["title"] == "Creep"
        assert result["artists"] == ["Radiohead"]
        assert result["album"] == "Pablo Honey"
        assert result["year"] == "1993"

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_skips_low_score_results(self, mock_search, _sleep):
        mock_search.return_value = {
            "recording-list": [
                {
                    "ext:score": "30",
                    "title": "Wrong Song",
                    "artist-credit": [{"artist": {"name": "Nobody"}}],
                }
            ]
        }
        assert mb_search(artists=["Radiohead"], title="Creep") is None

    @patch("src.lookup.time.sleep")
    @patch(
        "src.lookup.musicbrainzngs.search_recordings",
        side_effect=MusicBrainzError("network error"),
    )
    def test_returns_none_on_error(self, _mock, _sleep):
        assert mb_search(artists=["Radiohead"], title="Creep") is None

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_searches_with_title_only(self, mock_search, _sleep):
        mock_search.return_value = MB_SEARCH_RESPONSE
        result = mb_search(artists=[], title="Creep")
        assert result is not None
        call_args = mock_search.call_args
        assert "artist:" not in call_args.kwargs.get("query", call_args[1].get("query", ""))

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_skips_recording_without_title_or_artists(self, mock_search, _sleep):
        mock_search.return_value = {
            "recording-list": [
                {
                    "ext:score": "95",
                    "title": "",
                    "artist-credit": [{"artist": {"name": "Radiohead"}}],
                }
            ]
        }
        result = mb_search(artists=["Radiohead"], title="Creep")
        assert result is None

    @patch("src.lookup.time.sleep")
    @patch(
        "src.lookup.musicbrainzngs.search_recordings",
        side_effect=OSError("network I/O error"),
    )
    def test_returns_none_on_os_error(self, _mock, _sleep):
        assert mb_search(artists=["Radiohead"], title="Creep") is None

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_accepts_score_exactly_70(self, mock_search, _sleep):
        """Boundary: score == 70 è >= 70, deve essere accettato."""
        mock_search.return_value = {
            "recording-list": [
                {
                    "ext:score": "70",
                    "title": "Creep",
                    "artist-credit": [{"artist": {"name": "Radiohead"}}],
                    "release-list": [{"title": "Pablo Honey", "date": "1993"}],
                }
            ]
        }
        result = mb_search(artists=["Radiohead"], title="Creep")
        assert result is not None
        assert result["title"] == "Creep"

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_rejects_score_69(self, mock_search, _sleep):
        """Boundary: score == 69 è < 70, deve essere rifiutato."""
        mock_search.return_value = {
            "recording-list": [
                {
                    "ext:score": "69",
                    "title": "Creep",
                    "artist-credit": [{"artist": {"name": "Radiohead"}}],
                }
            ]
        }
        assert mb_search(artists=["Radiohead"], title="Creep") is None

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_searches_with_artist_only(self, mock_search, _sleep):
        """Con solo artista e titolo vuoto, la query non contiene 'recording:'."""
        mock_search.return_value = MB_SEARCH_RESPONSE
        mb_search(artists=["Radiohead"], title="")
        query = mock_search.call_args.kwargs.get("query", mock_search.call_args[1].get("query", ""))
        assert "recording:" not in query
        assert 'artist:"Radiohead"' in query

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_filters_non_dict_artist_credit_in_search(self, mock_search, _sleep):
        """Anche in mb_search, le stringhe join nell'artist-credit vengono filtrate."""
        mock_search.return_value = {
            "recording-list": [
                {
                    "ext:score": "90",
                    "title": "Under Pressure",
                    "artist-credit": [
                        {"artist": {"name": "Queen"}},
                        " & ",
                        {"artist": {"name": "David Bowie"}},
                    ],
                    "release-list": [],
                }
            ]
        }
        result = mb_search(artists=["Queen"], title="Under Pressure")
        assert result["artists"] == ["Queen", "David Bowie"]

    @patch("src.lookup.time.sleep")
    @patch("src.lookup.musicbrainzngs.search_recordings")
    def test_handles_no_releases_in_result(self, mock_search, _sleep):
        mock_search.return_value = {
            "recording-list": [
                {
                    "ext:score": "90",
                    "title": "Creep",
                    "artist-credit": [{"artist": {"name": "Radiohead"}}],
                }
            ]
        }
        result = mb_search(artists=["Radiohead"], title="Creep")
        assert result is not None
        assert result["title"] == "Creep"
        assert result["album"] == ""
        assert result["year"] == ""
