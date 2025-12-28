"""Smart import service for Excel/ODS files with intelligent anime matching."""

import re
import time
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImportResult:
    """Result of an import attempt for a single entry."""
    original_text: str
    parsed_titles: Dict[str, str]  # {english, japanese, romaji}
    matches: List[Dict]  # List of AniList matches
    status: str  # 'success', 'duplicate', 'no_match', 'error', 'cached'
    message: str
    confidence: float = 0.0  # 0-1 confidence score


class SmartImportService:
    """Service for importing anime from Excel/ODS files with smart matching."""

    # AniList rate limit: 90 requests per minute
    # We'll use 1 request per second to be safe (60/min)
    RATE_LIMIT_DELAY = 1.0

    # Minimum confidence threshold (0-1)
    MIN_CONFIDENCE = 0.4  # Only include matches with 40%+ confidence

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

        # Common uploader tags
        'Nyaa', 'U2', 'ADC', 'Share', 'Self-Rip', 'Self-Purchase',

        # Chinese/Japanese indicators that aren't titles
        '自抓', '自购', '感谢', 'thanks', 'Thanks'
    ]

    # Ambiguous keywords that might appear in anime titles
    # Only filter if they appear as standalone words
    AMBIGUOUS_KEYWORDS = [
        'OVA', 'OAD', 'Special', 'Movie', 'MOVIE', 'TV'
    ]

    def __init__(self, anilist_client, db_manager):
        """Initialize import service."""
        self.anilist_client = anilist_client
        self.db_manager = db_manager
        self.last_request_time = 0

        # Cache to avoid re-searching the same title
        # Format: {normalized_title: [list_of_matches]}
        self.search_cache: Dict[str, List[Dict]] = {}

        # Track AniList IDs added in this import session
        self.added_in_session: Set[int] = set()

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

    def parse_titles_from_entry(self, entry: str) -> Dict[str, str]:
        """
        Extract titles from bracketed format or fallback to whole text.
        Format: [Chinese][English/Romaji][Japanese][technical details...]
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
                # Clean it up first
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

        # First non-technical bracket is usually Chinese
        if len(non_technical_brackets) >= 1:
            titles['chinese'] = non_technical_brackets[0].strip()

        # Second bracket is usually English or Romaji
        if len(non_technical_brackets) >= 2:
            second = non_technical_brackets[1].strip()
            # If it contains mostly Latin characters, it's probably English/Romaji
            if self._is_latin_text(second):
                titles['english'] = second
                titles['romaji'] = second

        # Third bracket is usually Japanese
        if len(non_technical_brackets) >= 3:
            third = non_technical_brackets[2].strip()
            # If it contains Japanese characters
            if self._contains_japanese(third):
                titles['japanese'] = third

        # Look for better English names in later brackets
        for i in range(1, min(len(non_technical_brackets), 5)):
            text = non_technical_brackets[i].strip()
            if self._is_latin_text(text) and not self._looks_like_technical(text):
                if not titles['english'] or len(text) > len(titles['english']):
                    titles['english'] = text
                    if not titles['romaji']:
                        titles['romaji'] = text

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

    def _is_latin_text(self, text: str) -> bool:
        """Check if text is mostly Latin characters."""
        if not text:
            return False
        latin_chars = sum(1 for c in text if c.isascii() and (c.isalpha() or c.isspace()))
        return latin_chars / len(text) > 0.6

    def _contains_japanese(self, text: str) -> bool:
        """Check if text contains Japanese characters."""
        japanese_ranges = [
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
            (0x4E00, 0x9FFF),  # Kanji
        ]
        return any(
            any(start <= ord(char) <= end for start, end in japanese_ranges)
            for char in text
        )

    def _looks_like_technical(self, text: str) -> bool:
        """Check if text looks like technical metadata."""
        if not text or len(text) <= 1:
            return True

        text_lower = text.lower().strip()

        # Check for unambiguous technical keywords
        for keyword in self.TECHNICAL_KEYWORDS:
            if keyword.lower() in text_lower:
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
        ]

        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True

        return False

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

    def search_anime_smart(self, titles: Dict[str, str]) -> Tuple[List[Dict], bool]:
        """
        Search for anime using multiple strategies.
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

        # Strategy 1: Try English/Romaji title
        if titles.get('english'):
            self._rate_limit_wait()
            year = self._extract_year(titles['english'])
            matches = self.anilist_client.search_anime(titles['english'], year)

            for match in matches:
                if match['id'] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match['id'])

        # Strategy 2: Try Romaji if different from English
        if titles.get('romaji') and titles['romaji'] != titles.get('english', ''):
            self._rate_limit_wait()
            year = self._extract_year(titles['romaji'])
            matches = self.anilist_client.search_anime(titles['romaji'], year)

            for match in matches:
                if match['id'] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match['id'])

        # Strategy 3: Try Japanese title
        # Skip if we already have good matches
        if len(all_matches) < 3 and titles.get('japanese'):
            self._rate_limit_wait()
            matches = self.anilist_client.search_anime(titles['japanese'])

            for match in matches:
                if match['id'] not in seen_ids:
                    all_matches.append(match)
                    seen_ids.add(match['id'])

        # Strategy 4: Try cleaned-up English title
        if len(all_matches) < 3 and titles.get('english'):
            cleaned = self._clean_title_for_search(titles['english'])
            if cleaned != titles['english']:
                self._rate_limit_wait()
                matches = self.anilist_client.search_anime(cleaned)

                for match in matches:
                    if match['id'] not in seen_ids:
                        all_matches.append(match)
                        seen_ids.add(match['id'])

        # Strategy 5: Try Chinese title as last resort
        if len(all_matches) < 2 and titles.get('chinese'):
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

        # Exact match on English = 1.0
        if search_titles['english'] and search_titles['english'] == match_titles['english']:
            confidence = 1.0
        # Exact match on Romaji = 0.95
        elif search_titles['romaji'] and search_titles['romaji'] == match_titles['romaji']:
            confidence = 0.95
        # Exact match on Japanese = 0.9
        elif search_titles['japanese'] and search_titles['japanese'] == match_titles['native']:
            confidence = 0.9
        # Partial match
        else:
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

        return confidence

    def check_duplicate(self, match: Dict) -> Tuple[bool, Optional[str]]:
        """
        Check if anime already exists in database or was added in this session.
        Returns (is_duplicate, existing_entry_description)
        """
        anilist_id = match.get('id')
        title = match.get('title')
        year = match.get('year')

        # Check if added in this import session
        if anilist_id in self.added_in_session:
            return True, f"{title} ({year}) [added in this import]"

        # Check by AniList ID in database
        existing = self.db_manager.get_items(media_type="Anime")
        for item in existing:
            if item.anilist_id == anilist_id:
                return True, f"{item.title} ({item.year})"
            # Also check title + year combination
            if item.title == title and item.year == year:
                return True, f"{item.title} ({item.year})"

        return False, None

    def import_file(self, file_path: str, progress_callback=None) -> List[ImportResult]:
        """
        Import anime from file.
        Returns list of ImportResult objects.
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
            results.append(ImportResult(
                original_text="",
                parsed_titles={},
                matches=[],
                status='error',
                message=f"Failed to parse file: {e}"
            ))
            return results

        total_entries = len(entries)

        for i, entry in enumerate(entries):
            # Update progress
            if progress_callback:
                progress_callback(i + 1, total_entries, entry[:50])

            # Parse titles from entry
            titles = self.parse_titles_from_entry(entry)

            if not any(titles.values()):
                results.append(ImportResult(
                    original_text=entry,
                    parsed_titles=titles,
                    matches=[],
                    status='error',
                    message="Could not extract any titles from entry"
                ))
                continue

            # Search for matches (checks cache first)
            try:
                matches, was_cached = self.search_anime_smart(titles)

                if not matches:
                    results.append(ImportResult(
                        original_text=entry,
                        parsed_titles=titles,
                        matches=[],
                        status='no_match',
                        message="No matches found on AniList"
                    ))
                    continue

                # Calculate confidence for each match
                for match in matches:
                    match['_confidence'] = self.calculate_confidence(titles, match)

                # Filter by minimum confidence
                matches = [m for m in matches if m.get('_confidence', 0) >= self.MIN_CONFIDENCE]

                if not matches:
                    results.append(ImportResult(
                        original_text=entry,
                        parsed_titles=titles,
                        matches=[],
                        status='no_match',
                        message=f"No matches with sufficient confidence (min {self.MIN_CONFIDENCE:.0%})"
                    ))
                    continue

                # Sort by confidence
                matches.sort(key=lambda x: x.get('_confidence', 0), reverse=True)

                # Check for duplicates
                duplicate_matches = []
                new_matches = []

                for match in matches:
                    is_dup, dup_desc = self.check_duplicate(match)
                    if is_dup:
                        duplicate_matches.append((match, dup_desc))
                    else:
                        new_matches.append(match)

                # Determine status
                if was_cached:
                    if duplicate_matches and not new_matches:
                        status = 'duplicate'
                        message = f"All {len(duplicate_matches)} match(es) already in database [cached search]"
                    elif duplicate_matches and new_matches:
                        status = 'partial_duplicate'
                        message = f"Found {len(new_matches)} new match(es), {len(duplicate_matches)} duplicate(s) [cached search]"
                    else:
                        status = 'success'
                        message = f"Found {len(new_matches)} match(es) [cached search]"
                else:
                    if duplicate_matches and not new_matches:
                        status = 'duplicate'
                        message = f"All {len(duplicate_matches)} match(es) already in database"
                    elif duplicate_matches and new_matches:
                        status = 'partial_duplicate'
                        message = f"Found {len(new_matches)} new match(es), {len(duplicate_matches)} duplicate(s)"
                    else:
                        status = 'success'
                        message = f"Found {len(new_matches)} match(es)"

                results.append(ImportResult(
                    original_text=entry,
                    parsed_titles=titles,
                    matches=matches,
                    status=status,
                    message=message,
                    confidence=matches[0].get('_confidence', 0) if matches else 0
                ))

            except Exception as e:
                results.append(ImportResult(
                    original_text=entry,
                    parsed_titles=titles,
                    matches=[],
                    status='error',
                    message=f"Search error: {e}"
                ))

        return results

    def mark_as_added(self, anilist_ids: List[int]):
        """
        Mark AniList IDs as added in this session.
        Call this after adding items to the database.
        """
        self.added_in_session.update(anilist_ids)
