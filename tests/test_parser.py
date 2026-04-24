from src.parser import build_filename, parse_filename, slugify


class TestSlugify:
    def test_removes_unsafe_characters(self):
        assert slugify('song<>:"/\\|?*.mp3') == "song.mp3"

    def test_normalizes_unicode(self):
        # NFKC normalizza ﬁ → fi
        assert slugify("ofﬁce") == "office"

    def test_strips_dots_and_spaces(self):
        assert slugify("  hello. ") == "hello"

    def test_empty_returns_unknown(self):
        assert slugify("") == "unknown"

    def test_only_unsafe_chars_returns_unknown(self):
        assert slugify(':<>"/') == "unknown"

    def test_only_dots_and_spaces_returns_unknown(self):
        assert slugify("...   ") == "unknown"

    def test_whitespace_only_returns_unknown(self):
        assert slugify("   ") == "unknown"


class TestBuildFilename:
    def test_basic_format(self):
        result = build_filename(["Radiohead"], "Creep", ".mp3")
        assert result == "Radiohead-Creep.mp3"

    def test_multiple_artists(self):
        result = build_filename(["Jay-Z", "Kanye West"], "Otis", ".flac")
        assert result == "Jay-Z, Kanye West-Otis.flac"

    def test_empty_artists_uses_unknown(self):
        result = build_filename([], "Song", ".mp3")
        assert result == "Unknown Artist-Song.mp3"

    def test_empty_title_uses_unknown(self):
        result = build_filename(["Artist"], "", ".mp3")
        assert result == "Artist-Unknown Title.mp3"

    def test_filters_empty_and_whitespace_artists(self):
        result = build_filename(["", "Radiohead", "  "], "Creep", ".mp3")
        assert result == "Radiohead-Creep.mp3"

    def test_all_empty_artists_uses_unknown(self):
        result = build_filename(["", "  ", ""], "Song", ".mp3")
        assert result == "Unknown Artist-Song.mp3"

    def test_truncates_long_names_preserving_extension(self):
        long_title = "A" * 250
        result = build_filename(["X"], long_title, ".flac")
        assert len(result) <= 200
        assert result.endswith(".flac")

    def test_truncation_works_with_long_extension(self):
        long_title = "A" * 250
        result = build_filename(["X"], long_title, ".opus")
        assert len(result) <= 200
        assert result.endswith(".opus")

    def test_truncation_no_double_extension(self):
        """Verifica che il troncamento non produca doppia estensione."""
        long_title = "A" * 250
        result = build_filename(["X"], long_title, ".flac")
        assert result.count(".flac") == 1
        assert not result.endswith(".fla.flac")


class TestParseFilename:
    def test_artist_dash_title(self):
        artists, title = parse_filename("Radiohead - Creep")
        assert artists == ["Radiohead"]
        assert title == "Creep"

    def test_artist_emdash_title(self):
        artists, title = parse_filename("Radiohead — Creep")
        assert artists == ["Radiohead"]
        assert title == "Creep"

    def test_multiple_artists_feat(self):
        artists, title = parse_filename("Drake feat. Rihanna - Take Care")
        assert artists == ["Drake", "Rihanna"]
        assert title == "Take Care"

    def test_band_name_with_ampersand_stays_together(self):
        artists, title = parse_filename("Simon & Garfunkel - The Sound of Silence")
        assert artists == ["Simon & Garfunkel"]
        assert title == "The Sound of Silence"

    def test_feat_with_ampersand_splits_all(self):
        artists, title = parse_filename("Drake feat. Rihanna & Lil Wayne - Take Care")
        assert artists == ["Drake", "Rihanna", "Lil Wayne"]
        assert title == "Take Care"

    def test_strips_youtube_junk(self):
        artists, title = parse_filename("Radiohead - Creep [Official Video] (lyrics)")
        assert artists == ["Radiohead"]
        assert title == "Creep"

    def test_strips_leading_track_number(self):
        artists, title = parse_filename("01 - Radiohead - Creep")
        assert artists == ["Radiohead"]
        assert title == "Creep"

    def test_no_separator_returns_whole_as_title(self):
        artists, title = parse_filename("just a title")
        assert artists == []
        assert title == "just a title"

    def test_empty_string(self):
        artists, title = parse_filename("")
        assert artists == []
        assert title == ""

    def test_parenthesis_pattern_treats_parens_as_title(self):
        """Pattern 2 _PATTERNS[1]: group(1) = artista, group(2) = titolo in parentesi.

        'Creep (Radiohead)' → artista='Creep', titolo='Radiohead'.
        Questo pattern cattura formati come 'ArtistName (SongTitle)'.
        """
        artists, title = parse_filename("Creep (Radiohead)")
        assert artists == ["Creep"]
        assert title == "Radiohead"

    def test_track_number_with_dot_prefix(self):
        """Pattern track# con punto: '01. Artist - Title'."""
        artists, title = parse_filename("01. Radiohead - Creep")
        assert artists == ["Radiohead"]
        assert title == "Creep"

    def test_track_number_with_dot_no_space(self):
        artists, title = parse_filename("03.Massive Attack - Teardrop")
        assert artists == ["Massive Attack"]
        assert title == "Teardrop"

    def test_feat_ft_variant(self):
        artists, title = parse_filename("Drake ft Rihanna - Take Care")
        assert artists == ["Drake", "Rihanna"]
        assert title == "Take Care"

    def test_endash_separator(self):
        artists, title = parse_filename("Radiohead – Creep")
        assert artists == ["Radiohead"]
        assert title == "Creep"
