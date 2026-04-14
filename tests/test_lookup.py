from unittest.mock import patch

import acoustid as acoustid_lib
import pytest
from musicbrainzngs import MusicBrainzError

from src.config import Config
from src.lookup import _mb_recording_details, acoustid_lookup, mb_search


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
