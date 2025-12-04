"""Image loader utility for fetching and caching poster images."""

import requests
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QByteArray
from pathlib import Path


class ImageLoader:
    """Loads and caches images from URLs."""

    def __init__(self, cache_dir: str = "data/image_cache"):
        """Initialize image loader with cache directory."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_image(self, url: str, max_width: int = 100, max_height: int = 150) -> QPixmap:
        """
        Load image from URL or cache.

        Args:
            url: Image URL to load
            max_width: Maximum width to scale to
            max_height: Maximum height to scale to

        Returns:
            QPixmap of the image, or empty QPixmap if failed
        """
        if not url:
            return QPixmap()

        # Generate cache filename from URL
        cache_filename = self._url_to_filename(url)
        cache_path = self.cache_dir / cache_filename

        # Try to load from cache first
        if cache_path.exists():
            pixmap = QPixmap(str(cache_path))
            if not pixmap.isNull():
                return pixmap.scaled(max_width, max_height, aspectRatioMode=1, transformMode=1)

        # Download from URL
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)

            # Load and return
            byte_array = QByteArray(response.content)
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array)

            if not pixmap.isNull():
                return pixmap.scaled(max_width, max_height, aspectRatioMode=1, transformMode=1)

        except (requests.RequestException, IOError) as e:
            print(f"Failed to load image from {url}: {e}")

        return QPixmap()

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to safe filename for cache."""
        # Use last part of URL as filename
        parts = url.rstrip('/').split('/')
        filename = parts[-1] if parts else 'image.jpg'

        # Ensure it has an extension
        if '.' not in filename:
            filename += '.jpg'

        return filename
