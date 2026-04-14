import re
import unicodedata

# Pattern ordinati per probabilità (dal più comune al meno)
_PATTERNS = [
    # "Artist - Title"
    re.compile(r"^(.+?)\s*[-–—]\s*(.+)$"),
    # "Title (Artist)"
    re.compile(r"^(.+?)\s*\(([^)]+)\)\s*$"),
    # "Track# Artist - Title"
    re.compile(r"^\d+[\.\s]+(.+?)\s*[-–—]\s*(.+)$"),
]


def slugify(text: str) -> str:
    """Normalizza una stringa per usarla come nome file."""
    text = unicodedata.normalize("NFKC", text)
    # Rimuove caratteri non sicuri per filesystem
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = text.strip(". ")
    return text or "unknown"


def build_filename(artists: list[str], title: str, ext: str) -> str:
    """Costruisce il nome file nel formato {artisti}-{titolo}.ext"""
    artist_str = ", ".join(a.strip() for a in artists if a.strip())
    artist_str = artist_str or "Unknown Artist"
    title = title.strip() or "Unknown Title"
    stem = f"{slugify(artist_str)}-{slugify(title)}"
    # Limita lunghezza totale a 200 caratteri (limite filesystem sicuro)
    max_stem = 200 - len(ext)
    if len(stem) > max_stem:
        stem = stem[:max_stem]
    return f"{stem}{ext}"


def _split_artists(text: str) -> list[str]:
    """
    Divide la stringa artista in una lista.

    Splitta sempre su "feat."/"ft." (collaborazione esplicita).
    Splitta su "&" e "," solo se è presente anche feat/ft,
    per evitare di spezzare nomi di band come "Simon & Garfunkel".
    """
    has_feat = bool(re.search(r"\bfeat\.?\b|\bft\.?\b", text, flags=re.I))

    if has_feat:
        parts = re.split(r"\s*(?:feat\.?|ft\.?|&|,)\s*", text, flags=re.I)
    else:
        parts = re.split(r"\s*(?:feat\.?|ft\.?)\s*", text, flags=re.I)

    return [p.strip() for p in parts if p.strip()]


def parse_filename(stem: str) -> tuple[list[str], str]:
    """
    Tenta di estrarre (artisti, titolo) dal nome file (senza estensione).
    Ritorna ([], "") se non riesce.
    """
    # Pulizia preliminare
    stem = re.sub(
        r"\[.*?\]|\(official.*?\)|\(lyrics.*?\)|\(audio.*?\)"
        r"|\(lyric.*?\)|\(visual.*?\)|\(live.*?\)|\(feat.*?\)",
        "",
        stem,
        flags=re.I,
    )
    stem = re.sub(r"^\d+[\s\-\.]+", "", stem)
    stem = re.sub(r"\s+", " ", stem).strip()

    for pattern in _PATTERNS:
        m = pattern.match(stem)
        if m:
            a, t = m.group(1).strip(), m.group(2).strip()
            artists = _split_artists(a)
            return artists, t

    return [], stem  # Fallback: tutto come titolo
