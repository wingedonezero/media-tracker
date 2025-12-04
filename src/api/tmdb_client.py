"""TMDB API client for fetching movie and TV show data."""

import requests
from typing import List, Dict, Optional


class TMDBClient:
    """Client for The Movie Database API."""

    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

    def __init__(self, api_key: str = None):
        """
        Initialize TMDB client.

        To get a free API key:
        1. Create account at https://www.themoviedb.org/
        2. Go to Settings > API
        3. Request an API key (choose "Developer" option)
        4. Copy the API Key (v3 auth)
        """
        self.api_key = api_key
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make a request to TMDB API."""
        if not self.api_key:
            return None

        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}
        params['api_key'] = self.api_key

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"TMDB API error: {e}")
            return None

    def search_movie(self, query: str, year: int = None) -> List[Dict]:
        """Search for movies."""
        params = {'query': query}
        if year:
            params['year'] = year

        data = self._make_request('/search/movie', params)
        if not data:
            return []

        results = []
        for item in data.get('results', [])[:10]:  # Limit to top 10 results
            results.append({
                'id': item.get('id'),
                'title': item.get('title'),
                'year': item.get('release_date', '')[:4] if item.get('release_date') else None,
                'overview': item.get('overview'),
                'poster_url': f"{self.IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            })

        return results

    def search_tv(self, query: str, year: int = None) -> List[Dict]:
        """Search for TV shows."""
        params = {'query': query}
        if year:
            params['first_air_date_year'] = year

        data = self._make_request('/search/tv', params)
        if not data:
            return []

        results = []
        for item in data.get('results', [])[:10]:  # Limit to top 10 results
            results.append({
                'id': item.get('id'),
                'title': item.get('name'),
                'year': item.get('first_air_date', '')[:4] if item.get('first_air_date') else None,
                'overview': item.get('overview'),
                'poster_url': f"{self.IMAGE_BASE_URL}{item['poster_path']}" if item.get('poster_path') else None
            })

        return results

    def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Get detailed information about a movie."""
        data = self._make_request(f'/movie/{movie_id}')
        if not data:
            return None

        return {
            'id': data.get('id'),
            'title': data.get('title'),
            'year': data.get('release_date', '')[:4] if data.get('release_date') else None,
            'overview': data.get('overview'),
            'poster_url': f"{self.IMAGE_BASE_URL}{data['poster_path']}" if data.get('poster_path') else None
        }

    def get_tv_details(self, tv_id: int) -> Optional[Dict]:
        """Get detailed information about a TV show."""
        data = self._make_request(f'/tv/{tv_id}')
        if not data:
            return None

        return {
            'id': data.get('id'),
            'title': data.get('name'),
            'year': data.get('first_air_date', '')[:4] if data.get('first_air_date') else None,
            'overview': data.get('overview'),
            'poster_url': f"{self.IMAGE_BASE_URL}{data['poster_path']}" if data.get('poster_path') else None
        }
