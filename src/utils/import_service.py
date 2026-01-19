"""Smart import service for Excel/ODS files with intelligent media matching."""

import re
import time
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path
from abc import ABC, abstractmethod


@dataclass
class ImportResult:
    """Result of an import attempt for a single entry."""
    original_text: str
    parsed_titles: Dict[str, str]  # {english, japanese, romaji, etc.}
    matches: List[Dict]  # List of API matches
    status: str  # 'success', 'duplicate', 'no_match', 'error', 'cached', 'partial_duplicate'
    message: str
    confidence: float = 0.0  # 0-1 confidence score


class BaseImportService(ABC):
    """Base service for importing media from Excel/ODS files with smart matching."""

    # Rate limit delay (can be overridden by subclasses)
    RATE_LIMIT_DELAY = 2.5  # seconds

    # Minimum confidence threshold (0-1)
    MIN_CONFIDENCE = 0.35  # Only include matches with 35%+ confidence

    def __init__(self, db_manager):
        """Initialize import service."""
        self.db_manager = db_manager
        self.last_request_time = 0

        # Cache to avoid re-searching the same title
        # Format: {normalized_title: [list_of_matches]}
        self.search_cache: Dict[str, List[Dict]] = {}

        # Track IDs added in this import session (prevents duplicates within same import)
        self.added_in_session: Set[int] = set()

    @abstractmethod
    def get_media_type(self) -> str:
        """Return the media type for this service ('Anime', 'Movie', 'TV')."""
        pass

    @abstractmethod
    def parse_titles_from_entry(self, entry: str) -> Dict[str, str]:
        """
        Parse titles from entry text.
        Returns dict with title variants (english, romaji, japanese, etc.)
        """
        pass

    @abstractmethod
    def search_media(self, titles: Dict[str, str]) -> Tuple[List[Dict], bool]:
        """
        Search for media using the API.
        Returns (list of matches, was_cached).
        """
        pass

    @abstractmethod
    def calculate_confidence(self, titles: Dict[str, str], match: Dict) -> float:
        """
        Calculate confidence score for a match (0-1).
        Higher is better.
        """
        pass

    @abstractmethod
    def get_match_id(self, match: Dict) -> Optional[int]:
        """Get the unique ID from a match (anilist_id, tmdb_id, etc.)."""
        pass

    @abstractmethod
    def get_id_field_name(self) -> str:
        """Get the database field name for the ID (e.g., 'anilist_id', 'tmdb_id')."""
        pass

    def parse_ods_file(self, file_path: str) -> List[str]:
        """Parse ODS file and extract entries."""
        entries = []

        try:
            with zipfile.ZipFile(file_path, 'r') as ods:
                content = ods.read('content.xml')

            root = ET.fromstring(content)
            ns = {
                'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
                'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
                'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0'
            }

            tables = root.findall('.//table:table', ns)
            if tables:
                table = tables[0]
                rows = table.findall('.//table:table-row', ns)

                # Skip header row (row 0)
                for row in rows[1:]:
                    cells = row.findall('.//table:table-cell', ns)
                    if cells:
                        cell = cells[0]
                        text_elements = cell.findall('.//text:p', ns)
                        cell_text = ' '.join([t.text or '' for t in text_elements])

                        if cell_text.strip():
                            entries.append(cell_text.strip())

        except Exception as e:
            raise Exception(f"Failed to parse ODS file: {e}")

        return entries

    def parse_excel_file(self, file_path: str) -> List[str]:
        """Parse Excel file and extract entries."""
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(file_path, read_only=True)
            sheet = workbook.active

            entries = []
            # Skip header row
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row and row[0]:
                    entries.append(str(row[0]).strip())

            workbook.close()
            return entries

        except Exception as e:
            raise Exception(f"Failed to parse Excel file: {e}")

    def _normalize_title_for_cache(self, titles: Dict[str, str]) -> str:
        """
        Create a normalized cache key from titles.
        This helps us avoid re-searching similar entries.
        """
        # Use the best available title
        key_title = (
            titles.get('english') or
            titles.get('romaji') or
            titles.get('japanese') or
            titles.get('chinese') or
            titles.get('title') or
            ''
        )

        # Normalize: lowercase, remove special chars, collapse whitespace
        normalized = re.sub(r'[^\w\s]', ' ', key_title.lower())
        normalized = ' '.join(normalized.split())

        return normalized

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract year from text if present."""
        # Look for 4-digit year in parentheses or standalone
        year_match = re.search(r'\((\d{4})\)|(?:^|\s)(\d{4})(?:\s|$)', text)
        if year_match:
            year_str = year_match.group(1) or year_match.group(2)
            year = int(year_str)
            if 1950 <= year <= 2030:
                return year
        return None

    def _rate_limit_wait(self):
        """Wait to respect rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def check_duplicate(self, match: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if media already exists in database or was added in this session.
        Returns (is_duplicate, existing_entry_description)

        This method provides CRITICAL safeguards against database corruption:
        1. Checks session tracking to prevent duplicates within same import
        2. Checks database by unique ID (anilist_id, tmdb_id)
        3. Checks database by title+year combination
        """
        media_id = self.get_match_id(match)
        title = match.get('title')
        year = match.get('year')
        media_type = self.get_media_type()
        id_field_name = self.get_id_field_name()

        # Check if added in this import session
        if media_id and media_id in self.added_in_session:
            return True, f"{title} ({year}) [added in this import]"

        # Check by unique ID in database
        existing = self.db_manager.get_items(media_type=media_type)
        for item in existing:
            # Check by ID field (anilist_id, tmdb_id, etc.)
            item_id = getattr(item, id_field_name, None)
            if item_id and item_id == media_id:
                return True, f"{item.title} ({item.year})"

            # Also check title + year combination
            if item.title == title and item.year == year:
                return True, f"{item.title} ({item.year})"

        return False, None

    def import_file(self, file_path: str, progress_callback=None, result_callback=None) -> List[ImportResult]:
        """
        Import media from file.
        Returns list of ImportResult objects.

        This method ensures TRANSACTION SAFETY:
        1. Only reads and processes file - doesn't write to DB
        2. Returns results for user review
        3. Actual DB writes happen separately in dialog's add_matches_to_db
        4. Each DB write is individually protected with try/except

        Args:
            file_path: Path to Excel/ODS file
            progress_callback: Optional callback(current, total, entry) for progress updates
            result_callback: Optional callback(result) called for each processed entry
        """
        results = []

        # Clear session tracking
        self.search_cache.clear()
        self.added_in_session.clear()

        # Parse file based on extension
        file_ext = Path(file_path).suffix.lower()

        try:
            if file_ext == '.ods':
                entries = self.parse_ods_file(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                entries = self.parse_excel_file(file_path)
            else:
                raise Exception(f"Unsupported file format: {file_ext}")
        except Exception as e:
            # Return error result
            error_result = ImportResult(
                original_text="",
                parsed_titles={},
                matches=[],
                status='error',
                message=f"Failed to parse file: {e}"
            )
            results.append(error_result)
            if result_callback:
                result_callback(error_result)
            return results

        total_entries = len(entries)

        for i, entry in enumerate(entries):
            # Update progress
            if progress_callback:
                progress_callback(i + 1, total_entries, entry[:50])

            # Parse titles from entry
            titles = self.parse_titles_from_entry(entry)

            if not any(titles.values()):
                result = ImportResult(
                    original_text=entry,
                    parsed_titles=titles,
                    matches=[],
                    status='error',
                    message="Could not extract any titles from entry"
                )
                results.append(result)
                if result_callback:
                    result_callback(result)
                continue

            # Search for matches (checks cache first)
            try:
                matches, was_cached = self.search_media(titles)

                if not matches:
                    result = ImportResult(
                        original_text=entry,
                        parsed_titles=titles,
                        matches=[],
                        status='no_match',
                        message=f"No matches found"
                    )
                    results.append(result)
                    if result_callback:
                        result_callback(result)
                    continue

                # Calculate confidence for each match
                for match in matches:
                    match['_confidence'] = self.calculate_confidence(titles, match)

                # Filter by minimum confidence
                matches = [m for m in matches if m.get('_confidence', 0) >= self.MIN_CONFIDENCE]

                if not matches:
                    result = ImportResult(
                        original_text=entry,
                        parsed_titles=titles,
                        matches=[],
                        status='no_match',
                        message=f"No matches with sufficient confidence (min {self.MIN_CONFIDENCE:.0%})"
                    )
                    results.append(result)
                    if result_callback:
                        result_callback(result)
                    continue

                # Sort by confidence
                matches.sort(key=lambda x: x.get('_confidence', 0), reverse=True)

                # Check for duplicates (CRITICAL SAFEGUARD)
                duplicate_matches = []
                new_matches = []

                for match in matches:
                    is_dup, dup_desc = self.check_duplicate(match)
                    if is_dup:
                        duplicate_matches.append((match, dup_desc))
                    else:
                        new_matches.append(match)

                # Determine status
                cache_suffix = " [cached search]" if was_cached else ""
                if duplicate_matches and not new_matches:
                    status = 'duplicate'
                    message = f"All {len(duplicate_matches)} match(es) already in database{cache_suffix}"
                elif duplicate_matches and new_matches:
                    status = 'partial_duplicate'
                    message = f"Found {len(new_matches)} new match(es), {len(duplicate_matches)} duplicate(s){cache_suffix}"
                else:
                    status = 'success'
                    message = f"Found {len(new_matches)} match(es){cache_suffix}"

                result = ImportResult(
                    original_text=entry,
                    parsed_titles=titles,
                    matches=matches,
                    status=status,
                    message=message,
                    confidence=matches[0].get('_confidence', 0) if matches else 0
                )
                results.append(result)
                # Emit result immediately for live updates
                if result_callback:
                    result_callback(result)

            except Exception as e:
                result = ImportResult(
                    original_text=entry,
                    parsed_titles=titles,
                    matches=[],
                    status='error',
                    message=f"Search error: {e}"
                )
                results.append(result)
                if result_callback:
                    result_callback(result)

        return results

    def mark_as_added(self, media_ids: List[int]):
        """
        Mark media IDs as added in this session.
        Call this after adding items to the database.

        This is a CRITICAL SAFEGUARD to prevent duplicate additions
        within the same import session.
        """
        self.added_in_session.update(media_ids)


# ============================================================================
# ANIME IMPORT SERVICE
# ============================================================================

class AnimeImportService(BaseImportService):
    """Service for importing anime from Excel/ODS files with AniList matching."""

    # Comprehensive technical keywords to filter out
    # These are UNAMBIGUOUS technical terms that should NEVER appear in anime titles
    TECHNICAL_KEYWORDS = [
        # Video formats
        'BDMV', 'DVDISO', 'DVDMV', 'BluRay', 'Blu-ray', 'BD-BOX', 'BDISO',
        'WebDL', 'WEB-DL', 'WEBRip', 'HDRip', 'BRRip', 'DVDRip',

        # Resolutions and quality
        '1080p', '1080i', '720p', '480p', '480i', '2160p', '4K', '8K',

        # Video codecs
        'AVC', 'HEVC', 'H264', 'H.264', 'H265', 'H.265', 'x264', 'x265',
        'MPEG', 'MPEG-2', 'VP9', 'AV1',

        # Audio codecs
        'AAC', 'AC3', 'E-AC3', 'DTS', 'FLAC', 'MP3', 'LPCM',

        # File types
        'MKV', 'MP4', 'AVI', 'ISO',

        # Volume/Disc indicators
        'Vol.', 'Vol', 'Volume', 'DISC', 'Disc', 'Disk',
        'BD×', 'DVD×', 'BDx', 'DVDx',

        # Regions
        'R1', 'R2', 'R2J', 'R1US', 'USA', 'JPN', 'JP', 'NTSC', 'PAL',

        # Release info (ONLY unambiguous ones)
        'Fin', 'Remux', 'Encode', 'Rip', 'Source',

        # Common uploader tags and groups
        'Nyaa', 'U2', 'ADC', 'Share', 'Self-Rip', 'Self-Purchase',
        'VCB-Studio', 'VCB', 'TSDM', 'Kamigami', 'ANK-RAWS',
        'philosophy-raws', 'kakeruSMC', 'Lupin the Nerd',
        'taskforce', 'Ioroid', 'NAN0', 'CTM', 'Bikko',

        # Chinese/Japanese indicators that aren't titles
        '自抓', '自购', '感谢', 'thanks', 'Thanks', '台版',
        '自扫', '合集', '修正', '整合'
    ]

    # Ambiguous keywords that might appear in anime titles
    # Only filter if they appear as standalone words
    AMBIGUOUS_KEYWORDS = [
        'OVA', 'OAD', 'Special', 'Movie', 'MOVIE', 'TV'
    ]

    def __init__(self, anilist_client, db_manager):
        """Initialize anime import service."""
        super().__init__(db_manager)
        self.anilist_client = anilist_client

        # Initialize offline matcher (optional, graceful degradation if not available)
        try:
            from utils.offline_anime_matcher import OfflineAnimeMatcher
            self.offline_matcher = OfflineAnimeMatcher()
        except Exception as e:
            print(f"Offline matcher not available: {e}")
            self.offline_matcher = None

    def get_media_type(self) -> str:
        return "Anime"

    def get_match_id(self, match: Dict) -> Optional[int]:
        return match.get('id')

    def get_id_field_name(self) -> str:
        return "anilist_id"

    def parse_titles_from_entry(self, entry: str) -> Dict[str, str]:
        """
        Extract titles from bracketed format using smart language detection.
        Does NOT assume bracket order - categorizes by language instead.
        """
        titles = {
            'english': '',
            'romaji': '',
            'japanese': '',
            'chinese': ''
        }

        # Extract all bracketed content
        brackets = re.findall(r'\[([^\]]+)\]', entry)

        if not brackets:
            # Fallback: No brackets, use whole text if it's not too long
            if len(entry) < 100:
                cleaned = self._clean_non_bracketed_entry(entry)
                if cleaned:
                    titles['english'] = cleaned
                    titles['romaji'] = cleaned
            return titles

        # Filter out technical brackets
        non_technical_brackets = [
            b for b in brackets
            if not self._looks_like_technical(b) and len(b) > 1
        ]

        if not non_technical_brackets:
            # All brackets were technical, try fallback
            cleaned = self._clean_non_bracketed_entry(entry)
            if cleaned:
                titles['english'] = cleaned
                titles['romaji'] = cleaned
            return titles

        # Categorize brackets by language
        latin_brackets = []   # English/Romaji
        japanese_brackets = []  # Japanese
        chinese_brackets = []   # Chinese (has CJK but not Japanese-specific chars)

        for bracket in non_technical_brackets:
            bracket = bracket.strip()
            if not bracket:
                continue

            # Check language
            if self._contains_japanese(bracket):
                japanese_brackets.append(bracket)
            elif self._is_latin_text(bracket):
                latin_brackets.append(bracket)
            elif self._contains_cjk(bracket):
                # Has CJK chars but not Japanese-specific = Chinese
                chinese_brackets.append(bracket)

        # Assign titles based on language categories
        # English: Use longest Latin bracket (likely the full title)
        if latin_brackets:
            # Sort by length, take longest
            latin_brackets.sort(key=len, reverse=True)
            best_latin = self._clean_extracted_title(latin_brackets[0])
            if best_latin:
                titles['english'] = best_latin
                titles['romaji'] = best_latin

        # Japanese: Use first Japanese bracket
        if japanese_brackets:
            japanese_title = self._clean_extracted_title(japanese_brackets[0])
            if japanese_title:
                titles['japanese'] = japanese_title

        # Chinese: Use first Chinese bracket
        if chinese_brackets:
            titles['chinese'] = chinese_brackets[0]

        return titles

    def _clean_non_bracketed_entry(self, entry: str) -> str:
        """Clean up a non-bracketed entry to extract searchable title."""
        # Remove common separators and everything after them
        for sep in [' - ', ' – ', ' — ', '  ', '\t']:
            if sep in entry:
                parts = entry.split(sep)
                # Take first non-technical part
                for part in parts:
                    if not self._looks_like_technical(part) and len(part) > 2:
                        entry = part
                        break

        # Remove technical keywords
        cleaned = entry
        for keyword in self.TECHNICAL_KEYWORDS:
            cleaned = re.sub(r'\b' + re.escape(keyword) + r'\b', '', cleaned, flags=re.IGNORECASE)

        # Clean up whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip() if len(cleaned) > 2 else ''

    def _clean_extracted_title(self, title: str) -> str:
        """Clean extracted title by removing trailing junk markers."""
        if not title:
            return title

        # Remove trailing Chinese technical markers
        junk_suffixes = ['自抓', '自购', '感谢', '台版', '⾃抓', '⾃购', '合集', '修正', '整合']
        for suffix in junk_suffixes:
            if title.endswith(suffix):
                title = title[:-len(suffix)].strip()

        # Remove trailing @uploader patterns
        title = re.sub(r'\s*@[\w\-]+$', '', title)

        # Remove trailing uploader/group tags in parentheses or brackets
        title = re.sub(r'\s*[\(\[][\w\-\s]+@[\w\-]+[\)\]]$', '', title)

        # Remove trailing group names
        title = re.sub(r'\s*(?:VCB-Studio|TSDM|Kamigami).*$', '', title, flags=re.IGNORECASE)

        return title.strip()

    def _is_latin_text(self, text: str) -> bool:
        """Check if text is mostly Latin characters."""
        if not text:
            return False
        latin_chars = sum(1 for c in text if c.isascii() and (c.isalpha() or c.isspace()))
        return latin_chars / len(text) > 0.6

    def _contains_japanese(self, text: str) -> bool:
        """Check if text contains Japanese-specific characters (Hiragana/Katakana)."""
        japanese_ranges = [
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
        ]
        return any(
            any(start <= ord(char) <= end for start, end in japanese_ranges)
            for char in text
        )

    def _contains_cjk(self, text: str) -> bool:
        """Check if text contains CJK (Chinese/Japanese/Korean) characters."""
        cjk_ranges = [
            (0x4E00, 0x9FFF),   # CJK Unified Ideographs
            (0x3400, 0x4DBF),   # CJK Extension A
            (0x20000, 0x2A6DF), # CJK Extension B
            (0x3040, 0x309F),   # Hiragana
            (0x30A0, 0x30FF),   # Katakana
        ]
        return any(
            any(start <= ord(char) <= end for start, end in cjk_ranges)
            for char in text
        )

    def _looks_like_technical(self, text: str) -> bool:
        """Check if text looks like technical metadata."""
        if not text or len(text) <= 1:
            return True

        text_lower = text.lower().strip()

        # IMMEDIATELY filter out uploader patterns with @
        if '@' in text:
            return True

        # Filter out "Set X", "Vol X", "Part X" patterns
        set_patterns = [
            r'^set\s+\d+$',
            r'^vol\.?\s*\d+$',
            r'^volume\s+\d+$',
            r'^part\s+\d+$',
        ]
        for pattern in set_patterns:
            if re.match(pattern, text_lower):
                return True

        # Check for unambiguous technical keywords
        # BUT: Don't filter if it's a long text with trailing junk
        # (like "Some Anime Title 自抓" - the title is valid, just has suffix)
        has_substantial_content = len(text) > 10 and any(c.isalpha() for c in text[:10])

        for keyword in self.TECHNICAL_KEYWORDS:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                # If it's at the end and we have substantial content, don't filter
                # (we'll clean it later)
                if has_substantial_content and (
                    text_lower.endswith(keyword_lower) or
                    text_lower.endswith(keyword_lower + ' ')
                ):
                    continue  # Don't filter, will be cleaned later
                # Otherwise, filter it out
                return True

        # Check for ambiguous keywords - only filter if:
        # 1. The entire text is JUST the keyword (like "[OVA]")
        # 2. OR it's a short bracket with ONLY the keyword + numbers (like "[OVA 1-3]")
        for keyword in self.AMBIGUOUS_KEYWORDS:
            keyword_lower = keyword.lower()

            # If the text is EXACTLY the keyword (case-insensitive)
            if text_lower == keyword_lower:
                return True

            # If it's short and starts/ends with the keyword + numbers/punctuation
            # e.g., "OVA 1-3", "MOVIE 2", "Special Edition"
            if len(text) < 20:  # Short brackets are more likely technical
                # Check if it's mostly the keyword + technical stuff
                words = text_lower.split()
                if words and words[0] == keyword_lower:
                    # First word is the keyword, check if rest is technical
                    rest = ' '.join(words[1:])
                    if not rest or re.match(r'^[\d\-\s×x\.]+$', rest):
                        return True

        # Check for technical patterns
        patterns = [
            r'\d+p$',  # Ends with resolution like 1080p
            r'\d+i$',  # Ends with resolution like 480i
            r'vol\.?\s*\d+',  # Volume numbers
            r'disc?\s*[×x]\s*\d+',  # Disc count
            r'^\d{3,4}$',  # Just numbers
            r'bd[×x]\d+',  # BD count
            r'rev$',  # Revision indicator
            r'^\[.+\]$',  # Entire text is bracketed (uploader tag)
        ]

        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _filter_strict_matches(self, search_title: str, matches: List[Dict]) -> List[Dict]:
        """
        Strictly filter matches to remove false positives.
        For short titles (1-2 words), only keep very close matches.
        """
        if not search_title or not matches:
            return matches

        from rapidfuzz import fuzz

        search_lower = search_title.lower().strip()
        search_words = search_lower.split()
        search_word_count = len(search_words)

        filtered = []

        for match in matches:
            match_title = (match.get('title') or '').lower().strip()
            romaji_title = (match.get('romaji_title') or '').lower().strip()
            native_title = (match.get('native_title') or '').lower().strip()

            # Check all title variants
            for title_variant in [match_title, romaji_title, native_title]:
                if not title_variant:
                    continue

                variant_words = title_variant.split()
                variant_word_count = len(variant_words)

                # For short search terms (1-2 words), be VERY strict
                if search_word_count <= 2:
                    # Word count must be similar (within 1 word)
                    if abs(variant_word_count - search_word_count) > 1:
                        continue

                    # Calculate similarity ratio
                    ratio = fuzz.ratio(search_lower, title_variant)

                    # For very short titles (1 word), require near-perfect match
                    if search_word_count == 1:
                        if ratio >= 85:  # "AIR" vs "AIR" = 100, "AIR" vs "Airs" = 75
                            filtered.append(match)
                            break
                    # For 2-word titles, require high similarity
                    elif ratio >= 80:
                        filtered.append(match)
                        break
                else:
                    # For longer titles (3+ words), be more lenient
                    ratio = fuzz.ratio(search_lower, title_variant)
                    if ratio >= 70:
                        filtered.append(match)
                        break

        return filtered

    def search_media(self, titles: Dict[str, str]) -> Tuple[List[Dict], bool]:
        """
        Search for anime using multiple strategies.
        First tries offline database (fast, no rate limits), then falls back to API search.
        Returns (list of matches, was_cached).
        """
        # Check cache first
        cache_key = self._normalize_title_for_cache(titles)
        if cache_key and cache_key in self.search_cache:
            # Return cached results (deep copy to avoid mutation)
            cached = self.search_cache[cache_key]
            return [dict(m) for m in cached], True

        all_matches = []
        seen_ids = set()

        # STRATEGY 0: Try offline database as "spell checker" (if available)
        # Use it to find the BEST title variants to search with, not for final results
        if self.offline_matcher and self.offline_matcher.loaded:
            try:
                offline_matches = self.offline_matcher.match_titles(titles, min_score=85)

                if offline_matches:
                    # Get the best matched title from offline DB
                    # This is our "cleaned" title to search AniList with
                    best_match = offline_matches[0]  # (anilist_id, confidence, anime_data, title_type)
                    anilist_id, confidence, anime_data, _ = best_match

                    # Extract the best title variant from offline DB
                    cleaned_title = anime_data.get('title', '')

                    if cleaned_title and confidence >= 0.85:
                        # Use this cleaned title to SEARCH AniList (not fetch by ID)
                        self._rate_limit_wait()
                        year = self._extract_year(cleaned_title)
                        matches = self.anilist_client.search_anime(cleaned_title, year)

                        # Apply strict filtering to remove false positives
                        matches = self._filter_strict_matches(cleaned_title, matches)

                        if matches:
                            # For the BEST match, fetch all related content (seasons, OVAs, movies)
                            best_result = matches[0]
                            best_id = best_result.get('id')

                            if best_id:
                                self._rate_limit_wait()
                                # Get main anime + all relations
                                related_anime = self.anilist_client.get_anime_with_relations(best_id)

                                # Add all related content
                                for anime in related_anime:
                                    if anime['id'] not in seen_ids:
                                        all_matches.append(anime)
                                        seen_ids.add(anime['id'])

                        # If offline DB helped us find good results, use them
                        if all_matches:
                            self.search_cache[cache_key] = [dict(m) for m in all_matches]
                            return all_matches, False

            except Exception as e:
                print(f"Offline matching failed: {e}, falling back to API search")

        # FALLBACK: Regular API-based search strategies
        # Strategy 1: Try English/Romaji title
        if titles.get('english'):
            self._rate_limit_wait()
            year = self._extract_year(titles['english'])
            matches = self.anilist_client.search_anime(titles['english'], year)

            # Apply strict filtering for short titles
            matches = self._filter_strict_matches(titles['english'], matches)

            for match in matches:
                if match['id'] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match['id'])

            # If we got a good match, fetch relations
            if all_matches:
                best_id = all_matches[0].get('id')
                if best_id:
                    self._rate_limit_wait()
                    related_anime = self.anilist_client.get_anime_with_relations(best_id)

                    # Add all related content
                    for anime in related_anime:
                        if anime['id'] not in seen_ids:
                            all_matches.append(anime)
                            seen_ids.add(anime['id'])

                self.search_cache[cache_key] = [dict(m) for m in all_matches]
                return all_matches, False

        # Strategy 2: Try Romaji if different from English
        # SKIP if we already have ANY matches (save API calls)
        if len(all_matches) == 0 and titles.get('romaji') and titles['romaji'] != titles.get('english', ''):
            self._rate_limit_wait()
            year = self._extract_year(titles['romaji'])
            matches = self.anilist_client.search_anime(titles['romaji'], year)

            for match in matches:
                if match['id'] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match['id'])

            # If we got results, stop
            if len(all_matches) >= 3:
                self.search_cache[cache_key] = [dict(m) for m in all_matches]
                return all_matches, False

        # Strategy 3: Try Japanese title
        # ONLY if we have NO matches yet
        if len(all_matches) == 0 and titles.get('japanese'):
            self._rate_limit_wait()
            matches = self.anilist_client.search_anime(titles['japanese'])

            for match in matches:
                if match['id'] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match['id'])

            # If we got results, stop
            if len(all_matches) >= 3:
                self.search_cache[cache_key] = [dict(m) for m in all_matches]
                return all_matches, False

        # Strategy 4: Try cleaned-up English title
        # ONLY if we have NO matches yet
        if len(all_matches) == 0 and titles.get('english'):
            cleaned = self._clean_title_for_search(titles['english'])
            if cleaned and cleaned != titles['english']:
                self._rate_limit_wait()
                matches = self.anilist_client.search_anime(cleaned)

                for match in matches:
                    if match['id'] not in seen_ids:
                        all_matches.append(match)
                        seen_ids.add(match['id'])

        # Strategy 5: Try Chinese title as ABSOLUTE last resort
        # ONLY if we still have NO matches
        if len(all_matches) == 0 and titles.get('chinese'):
            chinese = titles['chinese']
            # Only if it looks like it might be searchable (has some Latin chars)
            if any(c.isascii() and c.isalpha() for c in chinese):
                self._rate_limit_wait()
                matches = self.anilist_client.search_anime(chinese)

                for match in matches:
                    if match['id'] not in seen_ids:
                        all_matches.append(match)
                        seen_ids.add(match['id'])

        # Cache the results
        if cache_key:
            self.search_cache[cache_key] = [dict(m) for m in all_matches]

        return all_matches, False

    def _clean_title_for_search(self, title: str) -> str:
        """Clean title for better search results."""
        # Remove year in parentheses
        title = re.sub(r'\(\d{4}\)', '', title)
        # Remove season indicators
        title = re.sub(r'(?i)\s*season\s*\d+', '', title)
        title = re.sub(r'(?i)\s*s\d+', '', title)
        # Remove part/season numbers
        title = re.sub(r'(?i)\s*part\s*\d+', '', title)
        # Remove special characters
        title = re.sub(r'[^\w\s]', ' ', title)
        # Clean up spaces
        title = ' '.join(title.split())
        return title.strip()

    def calculate_confidence(self, titles: Dict[str, str], match: Dict) -> float:
        """
        Calculate confidence score for a match (0-1).
        Higher is better.

        Args:
            titles: Parsed titles from entry
            match: AniList match data
        """
        confidence = 0.0

        match_titles = {
            'english': (match.get('title') or '').lower(),
            'romaji': (match.get('romaji_title') or '').lower(),
            'native': (match.get('native_title') or '').lower()
        }

        search_titles = {
            'english': (titles.get('english') or '').lower(),
            'romaji': (titles.get('romaji') or '').lower(),
            'japanese': (titles.get('japanese') or '').lower()
        }

        # Track which title types matched
        matches_found = []

        # Check exact matches
        english_match = search_titles['english'] and search_titles['english'] == match_titles['english']
        romaji_match = search_titles['romaji'] and search_titles['romaji'] == match_titles['romaji']
        japanese_match = search_titles['japanese'] and search_titles['japanese'] == match_titles['native']

        if english_match:
            matches_found.append('english')
            confidence = max(confidence, 0.95)
        if romaji_match:
            matches_found.append('romaji')
            confidence = max(confidence, 0.90)
        if japanese_match:
            matches_found.append('japanese')
            confidence = max(confidence, 0.90)

        # BONUS: If BOTH English AND Japanese match, this is VERY strong signal
        if english_match and japanese_match:
            confidence = 1.0  # Maximum confidence!

        # BONUS: If English/Romaji AND Japanese match
        elif (english_match or romaji_match) and japanese_match:
            confidence = 0.98  # Nearly perfect

        # If no exact matches, try partial matching
        if confidence == 0:
            # Check if any search title is contained in any match title
            for s_title in search_titles.values():
                if not s_title:
                    continue
                for m_title in match_titles.values():
                    if not m_title:
                        continue
                    if s_title in m_title or m_title in s_title:
                        confidence = max(confidence, 0.7)
                    # Check word overlap
                    s_words = set(s_title.split())
                    m_words = set(m_title.split())
                    if s_words and m_words:
                        overlap = len(s_words & m_words) / len(s_words | m_words)
                        confidence = max(confidence, overlap * 0.8)

        # Store which titles matched (useful for debugging)
        if hasattr(match, '__setitem__'):
            match['_matched_title_types'] = matches_found

        return confidence


# ============================================================================
# MOVIE IMPORT SERVICE
# ============================================================================

class MovieImportService(BaseImportService):
    """Service for importing movies from Excel/ODS files with TMDB matching."""

    def __init__(self, tmdb_client, db_manager):
        """Initialize movie import service."""
        super().__init__(db_manager)
        self.tmdb_client = tmdb_client

    def get_media_type(self) -> str:
        return "Movie"

    def get_match_id(self, match: Dict) -> Optional[int]:
        return match.get('id')

    def get_id_field_name(self) -> str:
        return "tmdb_id"

    def parse_titles_from_entry(self, entry: str) -> Dict[str, str]:
        """
        Parse titles from entry text.
        For movies, we expect simple format: "Movie Title" or "Movie Title (2020)"
        """
        titles = {'title': '', 'year': ''}

        # Clean the entry
        entry = entry.strip()

        # Extract year if present
        year = self._extract_year(entry)
        if year:
            titles['year'] = str(year)
            # Remove year from title
            entry = re.sub(r'\s*\(\d{4}\)\s*', ' ', entry).strip()

        # The rest is the title
        if entry:
            titles['title'] = entry

        return titles

    def search_media(self, titles: Dict[str, str]) -> Tuple[List[Dict], bool]:
        """
        Search for movies using TMDB.
        Returns (list of matches, was_cached).
        """
        # Check cache first
        cache_key = self._normalize_title_for_cache(titles)
        if cache_key and cache_key in self.search_cache:
            cached = self.search_cache[cache_key]
            return [dict(m) for m in cached], True

        title = titles.get('title', '')
        year_str = titles.get('year', '')
        year = int(year_str) if year_str and year_str.isdigit() else None

        if not title:
            return [], False

        # Rate limit
        self._rate_limit_wait()

        # Search TMDB
        try:
            matches = self.tmdb_client.search_movie(title, year)

            # Cache results
            if cache_key:
                self.search_cache[cache_key] = [dict(m) for m in matches]

            return matches, False
        except Exception as e:
            print(f"TMDB search error: {e}")
            return [], False

    def calculate_confidence(self, titles: Dict[str, str], match: Dict) -> float:
        """
        Calculate confidence score for a movie match (0-1).
        """
        from rapidfuzz import fuzz

        search_title = (titles.get('title') or '').lower().strip()
        match_title = (match.get('title') or '').lower().strip()

        if not search_title or not match_title:
            return 0.0

        # Calculate title similarity
        title_ratio = fuzz.ratio(search_title, match_title) / 100.0

        # Check year match
        search_year = titles.get('year')
        match_year = match.get('year')

        year_bonus = 0.0
        if search_year and match_year:
            try:
                search_year_int = int(search_year)
                match_year_int = int(match_year)
                if search_year_int == match_year_int:
                    year_bonus = 0.2  # Exact year match gives 20% bonus
                elif abs(search_year_int - match_year_int) <= 1:
                    year_bonus = 0.1  # Within 1 year gives 10% bonus
            except (ValueError, TypeError):
                pass

        # Base confidence on title similarity + year bonus
        confidence = min(1.0, title_ratio + year_bonus)

        return confidence


# ============================================================================
# TV IMPORT SERVICE
# ============================================================================

class TVImportService(BaseImportService):
    """Service for importing TV shows from Excel/ODS files with TMDB matching."""

    def __init__(self, tmdb_client, db_manager):
        """Initialize TV import service."""
        super().__init__(db_manager)
        self.tmdb_client = tmdb_client

    def get_media_type(self) -> str:
        return "TV"

    def get_match_id(self, match: Dict) -> Optional[int]:
        return match.get('id')

    def get_id_field_name(self) -> str:
        return "tmdb_id"

    def parse_titles_from_entry(self, entry: str) -> Dict[str, str]:
        """
        Parse titles from entry text.
        For TV shows, we expect simple format: "Show Title" or "Show Title (2020)"
        """
        titles = {'title': '', 'year': ''}

        # Clean the entry
        entry = entry.strip()

        # Extract year if present
        year = self._extract_year(entry)
        if year:
            titles['year'] = str(year)
            # Remove year from title
            entry = re.sub(r'\s*\(\d{4}\)\s*', ' ', entry).strip()

        # The rest is the title
        if entry:
            titles['title'] = entry

        return titles

    def search_media(self, titles: Dict[str, str]) -> Tuple[List[Dict], bool]:
        """
        Search for TV shows using TMDB.
        Returns (list of matches, was_cached).
        """
        # Check cache first
        cache_key = self._normalize_title_for_cache(titles)
        if cache_key and cache_key in self.search_cache:
            cached = self.search_cache[cache_key]
            return [dict(m) for m in cached], True

        title = titles.get('title', '')
        year_str = titles.get('year', '')
        year = int(year_str) if year_str and year_str.isdigit() else None

        if not title:
            return [], False

        # Rate limit
        self._rate_limit_wait()

        # Search TMDB
        try:
            matches = self.tmdb_client.search_tv(title, year)

            # Cache results
            if cache_key:
                self.search_cache[cache_key] = [dict(m) for m in matches]

            return matches, False
        except Exception as e:
            print(f"TMDB search error: {e}")
            return [], False

    def calculate_confidence(self, titles: Dict[str, str], match: Dict) -> float:
        """
        Calculate confidence score for a TV show match (0-1).
        """
        from rapidfuzz import fuzz

        search_title = (titles.get('title') or '').lower().strip()
        match_title = (match.get('title') or '').lower().strip()

        if not search_title or not match_title:
            return 0.0

        # Calculate title similarity
        title_ratio = fuzz.ratio(search_title, match_title) / 100.0

        # Check year match
        search_year = titles.get('year')
        match_year = match.get('year')

        year_bonus = 0.0
        if search_year and match_year:
            try:
                search_year_int = int(search_year)
                match_year_int = int(match_year)
                if search_year_int == match_year_int:
                    year_bonus = 0.2  # Exact year match gives 20% bonus
                elif abs(search_year_int - match_year_int) <= 1:
                    year_bonus = 0.1  # Within 1 year gives 10% bonus
            except (ValueError, TypeError):
                pass

        # Base confidence on title similarity + year bonus
        confidence = min(1.0, title_ratio + year_bonus)

        return confidence


# Backwards compatibility alias
SmartImportService = AnimeImportService
