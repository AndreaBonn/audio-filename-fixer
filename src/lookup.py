import functools
import subprocess
import time

import acoustid
import musicbrainzngs
from musicbrainzngs import MusicBrainzError

from src.config import REQUEST_DELAY, Config, log

# MusicBrainz setup
musicbrainzngs.set_useragent("MusicAutoTagger", "1.0", "https://github.com/local/music-tagger")
musicbrainzngs.set_rate_limit(REQUEST_DELAY)


@functools.cache
def _fpcalc_available() -> bool:
    try:
        subprocess.run(["fpcalc", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def acoustid_lookup(path: str, config: Config) -> dict | None:
    """
    Identifica la canzone tramite fingerprint audio con AcoustID.
    Richiede fpcalc installato e una API key gratuita su acoustid.org.
    """
    if not config.acoustid_api_key:
        log.debug("ACOUSTID_API_KEY non impostata, skip fingerprint")
        return None
    if not _fpcalc_available():
        log.debug("fpcalc non trovato, skip fingerprint")
        return None

    try:
        results = acoustid.match(config.acoustid_api_key, path, meta="recordings releasegroups")
        for score, recording_id, title, artist in results:
            if score < 0.5:
                continue
            log.info(f"  AcoustID match (score={score:.2f}): {artist} - {title}")
            return _mb_recording_details(recording_id)
    except (acoustid.AcoustidError, OSError) as e:
        log.debug(f"AcoustID error: {e}")
    return None


def _mb_recording_details(recording_id: str) -> dict | None:
    """Recupera titolo, artisti, album, anno da MusicBrainz per un recording ID."""
    try:
        time.sleep(REQUEST_DELAY)
        rec = musicbrainzngs.get_recording_by_id(recording_id, includes=["artists", "releases"])[
            "recording"
        ]

        title = rec.get("title", "")
        artists = [
            ac["artist"]["name"]
            for ac in rec.get("artist-credit", [])
            if isinstance(ac, dict) and "artist" in ac
        ]

        album, year = "", ""
        releases = rec.get("release-list", [])
        if releases:
            r = releases[0]
            album = r.get("title", "")
            year = r.get("date", "")[:4]

        if title and artists:
            return {"title": title, "artists": artists, "album": album, "year": year}
    except (MusicBrainzError, OSError) as e:
        log.debug(f"MB recording details error: {e}")
    return None


def mb_search(artists: list[str], title: str) -> dict | None:
    """Cerca su MusicBrainz per artista+titolo."""
    if not artists and not title:
        return None

    query_parts = []
    if title:
        query_parts.append(f'recording:"{title}"')
    if artists:
        query_parts.append(f'artist:"{artists[0]}"')
    query = " AND ".join(query_parts)

    try:
        time.sleep(REQUEST_DELAY)
        result = musicbrainzngs.search_recordings(query=query, limit=5)
        recordings = result.get("recording-list", [])

        for rec in recordings:
            score = int(rec.get("ext:score", 0))
            if score < 70:
                continue
            rec_title = rec.get("title", "")
            rec_artists = [
                ac["artist"]["name"]
                for ac in rec.get("artist-credit", [])
                if isinstance(ac, dict) and "artist" in ac
            ]
            if not rec_title or not rec_artists:
                continue

            album, year = "", ""
            releases = rec.get("release-list", [])
            if releases:
                r = releases[0]
                album = r.get("title", "")
                year = r.get("date", "")[:4]

            log.info(f"  MusicBrainz match (score={score}): {rec_artists} - {rec_title}")
            return {
                "title": rec_title,
                "artists": rec_artists,
                "album": album,
                "year": year,
            }

    except (MusicBrainzError, OSError) as e:
        log.debug(f"MusicBrainz search error: {e}")
    return None
