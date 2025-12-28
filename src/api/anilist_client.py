"""AniList API client for fetching anime data."""

import requests
import time
from typing import List, Dict, Optional


class AniListClient:
    """Client for AniList GraphQL API."""

    API_URL = "https://graphql.anilist.co"

    def __init__(self):
        """Initialize AniList client. No API key required!"""
        self.session = requests.Session()

    def _make_request(self, query: str, variables: dict = None, retry_count: int = 0) -> Optional[dict]:
        """
        Make a GraphQL request to AniList with retry logic for rate limiting.

        Args:
            query: GraphQL query string
            variables: Query variables
            retry_count: Current retry attempt (internal use)

        Returns:
            Response data or None if failed
        """
        max_retries = 3
        base_delay = 5  # Start with 5 second delay for 429 errors

        try:
            response = self.session.post(
                self.API_URL,
                json={'query': query, 'variables': variables or {}},
                timeout=10
            )

            # Handle rate limiting (429)
            if response.status_code == 429:
                if retry_count < max_retries:
                    # Exponential backoff: 5s, 10s, 20s
                    delay = base_delay * (2 ** retry_count)
                    print(f"Rate limit hit! Waiting {delay} seconds before retry {retry_count + 1}/{max_retries}...")
                    time.sleep(delay)
                    return self._make_request(query, variables, retry_count + 1)
                else:
                    print(f"AniList API error: Rate limit exceeded after {max_retries} retries")
                    return None

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

    def get_anime_with_relations(self, anime_id: int) -> List[Dict]:
        """
        Get anime and all its related content (sequels, prequels, side stories, etc.).
        Returns list with main anime first, followed by all related anime.
        """
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
                relations {
                    edges {
                        relationType
                        node {
                            id
                            type
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
                }
            }
        }
        '''

        data = self._make_request(graphql_query, {'id': anime_id})
        if not data or 'data' not in data:
            return []

        results = []
        main_item = data['data']['Media']

        # Add main anime first
        main_title = main_item['title'].get('english') or main_item['title'].get('romaji')
        results.append({
            'id': main_item.get('id'),
            'title': main_title,
            'native_title': main_item['title'].get('native'),
            'romaji_title': main_item['title'].get('romaji'),
            'year': main_item.get('seasonYear'),
            'overview': self._clean_description(main_item.get('description')),
            'poster_url': main_item.get('coverImage', {}).get('large'),
            'episodes': main_item.get('episodes'),
            'format': main_item.get('format'),
            'relation_type': 'MAIN'
        })

        # Add all related anime (sequels, prequels, side stories, etc.)
        if main_item.get('relations') and main_item['relations'].get('edges'):
            for edge in main_item['relations']['edges']:
                node = edge.get('node')
                relation_type = edge.get('relationType')

                # Only include anime (not manga, novels, etc.)
                if node and node.get('type') == 'ANIME':
                    related_title = node['title'].get('english') or node['title'].get('romaji')
                    results.append({
                        'id': node.get('id'),
                        'title': related_title,
                        'native_title': node['title'].get('native'),
                        'romaji_title': node['title'].get('romaji'),
                        'year': node.get('seasonYear'),
                        'overview': self._clean_description(node.get('description')),
                        'poster_url': node.get('coverImage', {}).get('large'),
                        'episodes': node.get('episodes'),
                        'format': node.get('format'),
                        'relation_type': relation_type  # SEQUEL, PREQUEL, SIDE_STORY, etc.
                    })

        return results

    @staticmethod
    def _clean_description(description: str) -> str:
        """Remove HTML tags from description."""
        if not description:
            return ""

        # Simple HTML tag removal
        import re
        clean = re.sub(r'<[^>]+>', '', description)
        return clean.strip()
