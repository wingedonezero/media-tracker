"""Offline anime matcher using anime-offline-database."""

import json
import unicodedata
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rapidfuzz import fuzz, process


class OfflineAnimeMatcher:
    """Matches anime titles using local offline database."""

    def __init__(self, db_path: str = None):
        """Initialize offline matcher."""
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "anime-offline-database.json"

        self.db_path = Path(db_path)
        self.anime_db: List[Dict] = []
        self.title_index: Dict[str, List[Dict]] = {}  # normalized_title -> [anime entries]
        self.loaded = False

        # Try to load database
        self.load_database()

    def load_database(self) -> bool:
        """Load and index the offline database."""
        if not self.db_path.exists():
            print(f"Offline database not found at {self.db_path}")
            print("Download it with:")
            print(f"  wget https://github.com/manami-project/anime-offline-database/raw/master/anime-offline-database-minified.json -O {self.db_path}")
            return False

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.anime_db = data.get('data', [])

            # Build title index
            for anime in self.anime_db:
                # Index all title variants
                titles_to_index = []

                # Main title
                if anime.get('title'):
                    titles_to_index.append(anime['title'])

                # Synonyms
                for synonym in anime.get('synonyms', []):
                    titles_to_index.append(synonym)

                # Index each title variant
                for title in titles_to_index:
                    normalized = self._normalize_title(title)
                    if normalized not in self.title_index:
                        self.title_index[normalized] = []
                    self.title_index[normalized].append(anime)

            self.loaded = True
            print(f"Loaded offline database: {len(self.anime_db)} anime, {len(self.title_index)} unique titles")
            return True

        except Exception as e:
            print(f"Failed to load offline database: {e}")
            return False

    def _normalize_title(self, title: str) -> str:
        """Normalize title for matching."""
        if not title:
            return ""

        # Normalize Unicode (⽂ → 文)
        title = unicodedata.normalize('NFKC', title)

        # Lowercase
        title = title.lower()

        # Remove special punctuation that breaks matching
        for char in [':', '：', '~', '〜', '!', '！', '?', '？', '-', '–', '—']:
            title = title.replace(char, ' ')

        # Collapse whitespace
        title = ' '.join(title.split())

        return title

    def _extract_anilist_id(self, anime: Dict) -> Optional[int]:
        """Extract AniList ID from anime entry."""
        sources = anime.get('sources', [])
        for source in sources:
            if 'anilist.co' in source:
                # Extract ID from URL like "https://anilist.co/anime/12345"
                parts = source.rstrip('/').split('/')
                if parts:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        continue
        return None

    def match_titles(self, titles: Dict[str, str], min_score: int = 80) -> List[Tuple[int, float, Dict]]:
        """
        Match titles against offline database.

        Args:
            titles: Dict with 'english', 'romaji', 'japanese', 'chinese' keys
            min_score: Minimum fuzzy match score (0-100)

        Returns:
            List of (anilist_id, confidence, anime_data) tuples, sorted by confidence
        """
        if not self.loaded:
            return []

        # Collect all search titles
        search_titles = []
        for key in ['english', 'romaji', 'japanese', 'chinese']:
            if titles.get(key):
                search_titles.append(titles[key])

        if not search_titles:
            return []

        # Find matches for each search title
        all_matches = {}  # anilist_id -> (best_score, anime_data, matched_title_type)

        for search_title in search_titles:
            normalized_search = self._normalize_title(search_title)

            # Try exact match first
            if normalized_search in self.title_index:
                for anime in self.title_index[normalized_search]:
                    anilist_id = self._extract_anilist_id(anime)
                    if anilist_id:
                        if anilist_id not in all_matches or all_matches[anilist_id][0] < 100:
                            # Determine which title type matched
                            title_type = self._get_title_type(search_title, titles)
                            all_matches[anilist_id] = (100.0, anime, title_type)

            # Fuzzy match against all titles
            # Build list of (title, anime) pairs
            title_anime_pairs = []
            for norm_title, anime_list in self.title_index.items():
                for anime in anime_list:
                    title_anime_pairs.append((norm_title, anime))

            # Use rapidfuzz for fuzzy matching
            # Extract just the titles for matching
            titles_only = [pair[0] for pair in title_anime_pairs]

            # Find best matches
            fuzzy_matches = process.extract(
                normalized_search,
                titles_only,
                scorer=fuzz.ratio,
                limit=10,
                score_cutoff=min_score
            )

            for matched_title, score, _ in fuzzy_matches:
                # Find the anime entries for this title
                for anime in self.title_index[matched_title]:
                    anilist_id = self._extract_anilist_id(anime)
                    if anilist_id:
                        # Only update if this is a better score
                        if anilist_id not in all_matches or all_matches[anilist_id][0] < score:
                            title_type = self._get_title_type(search_title, titles)
                            all_matches[anilist_id] = (float(score), anime, title_type)

        # Convert to list and sort by score
        results = []
        for anilist_id, (score, anime, title_type) in all_matches.items():
            # Convert score (0-100) to confidence (0-1)
            confidence = score / 100.0
            results.append((anilist_id, confidence, anime, title_type))

        # Sort by confidence (highest first)
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def _get_title_type(self, search_title: str, titles: Dict[str, str]) -> str:
        """Determine which type of title this is."""
        for key in ['english', 'romaji', 'japanese', 'chinese']:
            if titles.get(key) == search_title:
                return key
        return 'unknown'

    def get_match_info(self, anime: Dict) -> Dict:
        """Extract useful info from anime entry."""
        return {
            'title': anime.get('title', 'Unknown'),
            'type': anime.get('type', 'Unknown'),
            'episodes': anime.get('episodes', 0),
            'year': self._extract_year(anime),
            'synonyms': anime.get('synonyms', [])
        }

    def _extract_year(self, anime: Dict) -> Optional[int]:
        """Extract year from anime entry."""
        # Try animeSeason field
        if 'animeSeason' in anime:
            season = anime['animeSeason']
            if 'year' in season:
                return season['year']

        # Try parsing from sources or other fields
        # This is a fallback and might not always work
        return None
