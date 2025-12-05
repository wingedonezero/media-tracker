"""AniList API client for fetching anime data."""

import requests
from typing import List, Dict, Optional


class AniListClient:
    """Client for AniList GraphQL API."""

    API_URL = "https://graphql.anilist.co"

    def __init__(self):
        """Initialize AniList client. No API key required!"""
        self.session = requests.Session()

    def _make_request(self, query: str, variables: dict = None) -> Optional[dict]:
        """Make a GraphQL request to AniList."""
        try:
            response = self.session.post(
                self.API_URL,
                json={'query': query, 'variables': variables or {}},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"AniList API error: {e}")
            return None

    def search_anime(self, query: str, year: int = None) -> List[Dict]:
        """Search for anime."""
        graphql_query = '''
        query ($search: String, $year: Int) {
            Page(page: 1, perPage: 10) {
                media(search: $search, type: ANIME, seasonYear: $year) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    seasonYear
                    description
                    coverImage {
                        large
                    }
                }
            }
        }
        '''

        variables = {'search': query}
        if year:
            variables['year'] = year

        data = self._make_request(graphql_query, variables)
        if not data or 'data' not in data:
            return []

        results = []
        for item in data['data']['Page']['media']:
            # Prefer English title, fall back to Romaji
            title = item['title'].get('english') or item['title'].get('romaji')
            native_title = item['title'].get('native')
            romaji_title = item['title'].get('romaji')

            results.append({
                'id': item.get('id'),
                'title': title,
                'native_title': native_title,
                'romaji_title': romaji_title,
                'year': item.get('seasonYear'),
                'overview': self._clean_description(item.get('description')),
                'poster_url': item.get('coverImage', {}).get('large')
            })

        return results

    def get_anime_details(self, anime_id: int) -> Optional[Dict]:
        """Get detailed information about an anime."""
        graphql_query = '''
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                seasonYear
                description
                coverImage {
                    large
                }
                episodes
                format
            }
        }
        '''

        data = self._make_request(graphql_query, {'id': anime_id})
        if not data or 'data' not in data:
            return None

        item = data['data']['Media']
        title = item['title'].get('english') or item['title'].get('romaji')
        native_title = item['title'].get('native')
        romaji_title = item['title'].get('romaji')

        return {
            'id': item.get('id'),
            'title': title,
            'native_title': native_title,
            'romaji_title': romaji_title,
            'year': item.get('seasonYear'),
            'overview': self._clean_description(item.get('description')),
            'poster_url': item.get('coverImage', {}).get('large'),
            'episodes': item.get('episodes'),
            'format': item.get('format')
        }

    @staticmethod
    def _clean_description(description: str) -> str:
        """Remove HTML tags from description."""
        if not description:
            return ""

        # Simple HTML tag removal
        import re
        clean = re.sub(r'<[^>]+>', '', description)
        return clean.strip()
