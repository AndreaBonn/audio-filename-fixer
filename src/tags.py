from pathlib import Path

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TALB, TDRC, TIT2, TPE1, ID3NoHeaderError
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

from src.config import log
from src.parser import build_filename


def read_existing_tags(path: str) -> dict:
    """Legge i tag esistenti dal file audio. Ritorna dict con chiavi standard."""
    result = {"title": "", "artists": [], "album": "", "year": "", "track": ""}
    try:
        audio = MutagenFile(path, easy=True)
        if audio is None:
            log.warning(f"Formato audio non riconosciuto: {path}")
            return result
        result["title"] = audio.get("title", [""])[0]
        result["artists"] = audio.get("artist", [])
        result["album"] = audio.get("album", [""])[0]
        result["year"] = audio.get("date", [""])[0][:4]
        result["track"] = audio.get("tracknumber", [""])[0]
    except PermissionError:
        log.error(f"Permesso negato in lettura tag: {path}")
    except OSError as e:
        log.warning(f"Errore I/O lettura tag {path}: {e}")
    except Exception as e:
        log.error(f"Errore inatteso lettura tag {path}: {e}", exc_info=True)
    return result


def tags_look_complete(tags: dict) -> bool:
    """True se i tag esistenti sembrano già a posto (title + almeno un artista)."""
    has_title = bool(tags.get("title", "").strip())
    has_artist = any(a.strip() for a in tags.get("artists", []))
    return has_title and has_artist


def write_tags(path: str, info: dict, *, dry_run: bool = False) -> bool:
    """Scrive i metadati nel file audio. Ritorna True se la scrittura ha successo."""
    if dry_run:
        log.info(f"  [DRY RUN] Scrittura tag: {info}")
        return True

    ext = Path(path).suffix.lower()
    title = info.get("title", "")
    artists = info.get("artists", [])
    album = info.get("album", "")
    year = info.get("year", "")
    artist_str = "; ".join(artists)

    try:
        if ext == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            tags["TIT2"] = TIT2(encoding=3, text=title)
            tags["TPE1"] = TPE1(encoding=3, text=artist_str)
            if album:
                tags["TALB"] = TALB(encoding=3, text=album)
            if year:
                tags["TDRC"] = TDRC(encoding=3, text=year)
            tags.save(path)

        elif ext == ".flac":
            audio = FLAC(path)
            audio["title"] = title
            audio["artist"] = artist_str
            if album:
                audio["album"] = album
            if year:
                audio["date"] = year
            audio.save()

        elif ext in (".m4a", ".aac"):
            audio = MP4(path)
            audio["\xa9nam"] = title
            audio["\xa9ART"] = artist_str
            if album:
                audio["\xa9alb"] = album
            if year:
                audio["\xa9day"] = year
            audio.save()

        elif ext in (".ogg", ".opus"):
            audio = OggVorbis(path)
            audio["title"] = title
            audio["artist"] = artist_str
            if album:
                audio["album"] = album
            if year:
                audio["date"] = year
            audio.save()

        else:
            audio = MutagenFile(path, easy=True)
            if audio is None:
                log.warning(f"  Formato non supportato per scrittura tag: {ext}")
                return False
            audio["title"] = title
            audio["artist"] = artist_str
            if album:
                audio["album"] = album
            if year:
                audio["date"] = year
            audio.save()

        log.info(f"  ✓ Tag scritti: {artist_str} - {title}")
        return True

    except PermissionError:
        log.error(f"  ✗ Permesso negato: impossibile scrivere tag in {path}")
        return False
    except OSError as e:
        log.error(f"  ✗ Errore I/O scrittura tag {path}: {e}")
        return False
    except Exception as e:
        log.error(f"  ✗ Errore inatteso scrittura tag {path}: {e}", exc_info=True)
        return False


def rename_file(path: str, info: dict, *, dry_run: bool = False) -> str:
    """
    Rinomina il file nel formato {artisti}-{titolo}.ext
    Ritorna il nuovo path (o quello originale in caso di errore/dry_run).
    """
    p = Path(path)
    new_name = build_filename(info["artists"], info["title"], p.suffix.lower())
    new_path = p.parent / new_name

    # Verifica path traversal
    if not new_path.resolve().is_relative_to(p.parent.resolve()):
        log.error(f"  ✗ Path traversal bloccato per {new_name}")
        return path

    if new_path == p:
        log.info(f"  Nome già corretto: {p.name}")
        return path

    if new_path.exists():
        log.warning(f"  File già esistente: {new_name}, aggiungo suffisso")
        stem = new_path.stem
        new_path = p.parent / f"{stem}_dup{p.suffix}"

    if dry_run:
        log.info(f"  [DRY RUN] Rinomina: {p.name} → {new_name}")
        return path

    try:
        p.rename(new_path)
        log.info(f"  ✓ Rinominato: {p.name} → {new_name}")
        return str(new_path)
    except PermissionError:
        log.error(f"  ✗ Permesso negato: impossibile rinominare {path}")
        return path
    except OSError as e:
        log.error(f"  ✗ Errore rinomina {path}: {e}")
        return path
