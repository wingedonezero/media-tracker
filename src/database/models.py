"""Data models for media tracker."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class MediaItem:
    """Represents a media item (TV show, movie, or anime)."""

    id: Optional[int] = None
    title: str = ""
    native_title: Optional[str] = None  # Japanese/native title for anime
    year: Optional[int] = None
    media_type: str = "Movie"  # TV/Movie/Anime
    status: str = "To Download"  # On Drive/To Download/To Work On
    quality_type: Optional[str] = None  # Remux/WebDL/BluRay/etc
    source: Optional[str] = None
    notes: Optional[str] = None
    tmdb_id: Optional[int] = None
    anilist_id: Optional[int] = None
    poster_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self):
        """Convert to dictionary for database operations."""
        return {
            'id': self.id,
            'title': self.title,
            'native_title': self.native_title,
            'year': self.year,
            'media_type': self.media_type,
            'status': self.status,
            'quality_type': self.quality_type,
            'source': self.source,
            'notes': self.notes,
            'tmdb_id': self.tmdb_id,
            'anilist_id': self.anilist_id,
            'poster_url': self.poster_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create MediaItem from dictionary."""
        return cls(**data)
