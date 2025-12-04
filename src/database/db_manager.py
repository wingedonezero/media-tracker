"""Database manager for SQLite operations."""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from database.models import MediaItem


class DatabaseManager:
    """Manages SQLite database operations."""

    def __init__(self, db_path: str = "data/media_tracker.db"):
        """Initialize database manager."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    native_title TEXT,
                    year INTEGER,
                    media_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    quality_type TEXT,
                    source TEXT,
                    notes TEXT,
                    tmdb_id INTEGER,
                    anilist_id INTEGER,
                    poster_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Add native_title column if it doesn't exist (migration)
            try:
                cursor.execute('ALTER TABLE media_items ADD COLUMN native_title TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists
                pass

            # Create indexes for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_media_type_status
                ON media_items(media_type, status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_title
                ON media_items(title)
            ''')
            conn.commit()

    def add_item(self, item: MediaItem) -> int:
        """Add a new media item to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO media_items
                (title, native_title, year, media_type, status, quality_type, source, notes,
                 tmdb_id, anilist_id, poster_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.title, item.native_title, item.year, item.media_type, item.status,
                item.quality_type, item.source, item.notes,
                item.tmdb_id, item.anilist_id, item.poster_url
            ))
            conn.commit()
            return cursor.lastrowid

    def update_item(self, item: MediaItem):
        """Update an existing media item."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE media_items
                SET title=?, native_title=?, year=?, media_type=?, status=?, quality_type=?,
                    source=?, notes=?, tmdb_id=?, anilist_id=?, poster_url=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                item.title, item.native_title, item.year, item.media_type, item.status,
                item.quality_type, item.source, item.notes,
                item.tmdb_id, item.anilist_id, item.poster_url, item.id
            ))
            conn.commit()

    def delete_item(self, item_id: int):
        """Delete a media item."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM media_items WHERE id=?', (item_id,))
            conn.commit()

    def get_items(self, media_type: str = None, status: str = None) -> List[MediaItem]:
        """Get media items with optional filtering."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM media_items WHERE 1=1'
            params = []

            if media_type:
                query += ' AND media_type=?'
                params.append(media_type)

            if status:
                query += ' AND status=?'
                params.append(status)

            query += ' ORDER BY title'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            items = []
            for row in rows:
                item = MediaItem(
                    id=row['id'],
                    title=row['title'],
                    native_title=row.get('native_title'),
                    year=row['year'],
                    media_type=row['media_type'],
                    status=row['status'],
                    quality_type=row['quality_type'],
                    source=row['source'],
                    notes=row['notes'],
                    tmdb_id=row['tmdb_id'],
                    anilist_id=row['anilist_id'],
                    poster_url=row['poster_url'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                items.append(item)

            return items

    def search_items(self, search_term: str, media_type: str = None) -> List[MediaItem]:
        """Search for media items by title or notes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT * FROM media_items
                WHERE (title LIKE ? OR notes LIKE ?)
            '''
            params = [f'%{search_term}%', f'%{search_term}%']

            if media_type:
                query += ' AND media_type=?'
                params.append(media_type)

            query += ' ORDER BY title'

            cursor.execute(query, params)
            rows = cursor.fetchall()

            items = []
            for row in rows:
                item = MediaItem(
                    id=row['id'],
                    title=row['title'],
                    native_title=row.get('native_title'),
                    year=row['year'],
                    media_type=row['media_type'],
                    status=row['status'],
                    quality_type=row['quality_type'],
                    source=row['source'],
                    notes=row['notes'],
                    tmdb_id=row['tmdb_id'],
                    anilist_id=row['anilist_id'],
                    poster_url=row['poster_url'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                items.append(item)

            return items

    def check_duplicate(self, title: str, year: Optional[int], media_type: str) -> bool:
        """Check if a media item already exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM media_items
                WHERE title=? AND year=? AND media_type=?
            ''', (title, year, media_type))
            result = cursor.fetchone()
            return result['count'] > 0
