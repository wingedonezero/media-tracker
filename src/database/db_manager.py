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
                    romaji_title TEXT,
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

            # Add romaji_title column if it doesn't exist (migration)
            try:
                cursor.execute('ALTER TABLE media_items ADD COLUMN romaji_title TEXT')
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
                (title, native_title, romaji_title, year, media_type, status, quality_type, source, notes,
                 tmdb_id, anilist_id, poster_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.title, item.native_title, item.romaji_title, item.year, item.media_type, item.status,
                item.quality_type, item.source, item.notes,
                item.tmdb_id, item.anilist_id, item.poster_url
            ))
            conn.commit()
            return cursor.lastrowid

    def add_items_batch(self, items: List[MediaItem], skip_duplicates: bool = True) -> dict:
        """Add multiple items in a single transaction.

        Args:
            items: List of MediaItem objects to add
            skip_duplicates: If True, skip items that already exist. If False, fail on duplicates.

        Returns:
            Dictionary with 'added', 'skipped', and 'errors' counts and lists
        """
        result = {
            'added': 0,
            'skipped': 0,
            'errors': 0,
            'added_items': [],
            'skipped_items': [],
            'error_items': []
        }

        if not items:
            return result

        conn = self.get_connection()
        try:
            # Begin explicit transaction
            conn.execute("BEGIN TRANSACTION")
            cursor = conn.cursor()

            for item in items:
                try:
                    # Check for duplicates (using same transaction cursor)
                    if self.check_duplicate_by_id(item, cursor=cursor):
                        if skip_duplicates:
                            result['skipped'] += 1
                            result['skipped_items'].append(item.title)
                            continue
                        else:
                            raise ValueError(f"Duplicate item: {item.title}")

                    # Insert the item
                    cursor.execute('''
                        INSERT INTO media_items
                        (title, native_title, romaji_title, year, media_type, status, quality_type, source, notes,
                         tmdb_id, anilist_id, poster_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.title, item.native_title, item.romaji_title, item.year, item.media_type, item.status,
                        item.quality_type, item.source, item.notes,
                        item.tmdb_id, item.anilist_id, item.poster_url
                    ))

                    result['added'] += 1
                    result['added_items'].append(item.title)

                except Exception as e:
                    result['errors'] += 1
                    result['error_items'].append(f"{item.title}: {str(e)}")
                    # On error, rollback the entire transaction
                    conn.rollback()
                    raise

            # Commit the transaction (all items added successfully)
            conn.commit()

        except Exception as e:
            # Rollback on any error
            try:
                conn.rollback()
            except:
                pass
            raise

        finally:
            conn.close()

        return result

    def update_item(self, item: MediaItem):
        """Update an existing media item."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE media_items
                SET title=?, native_title=?, romaji_title=?, year=?, media_type=?, status=?, quality_type=?,
                    source=?, notes=?, tmdb_id=?, anilist_id=?, poster_url=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                item.title, item.native_title, item.romaji_title, item.year, item.media_type, item.status,
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
                # Handle native_title and romaji_title for backward compatibility
                native_title = row['native_title'] if 'native_title' in row.keys() else None
                romaji_title = row['romaji_title'] if 'romaji_title' in row.keys() else None

                item = MediaItem(
                    id=row['id'],
                    title=row['title'],
                    native_title=native_title,
                    romaji_title=romaji_title,
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

            # For anime, search all three title fields
            if media_type == "Anime":
                query = '''
                    SELECT * FROM media_items
                    WHERE (title LIKE ? OR notes LIKE ? OR native_title LIKE ? OR romaji_title LIKE ?)
                '''
                params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']
            else:
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
                # Handle native_title and romaji_title for backward compatibility
                native_title = row['native_title'] if 'native_title' in row.keys() else None
                romaji_title = row['romaji_title'] if 'romaji_title' in row.keys() else None

                item = MediaItem(
                    id=row['id'],
                    title=row['title'],
                    native_title=native_title,
                    romaji_title=romaji_title,
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

    def check_duplicate_by_id(self, item: MediaItem, cursor=None) -> bool:
        """Check if item exists by API ID (tmdb_id/anilist_id) or title+year.

        More robust duplicate detection for multi-select.

        Args:
            item: MediaItem to check
            cursor: Optional cursor to use (for transactions). If None, creates new connection.
        """
        if cursor is None:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                return self._check_duplicate_by_id_impl(item, cursor)
        else:
            return self._check_duplicate_by_id_impl(item, cursor)

    def _check_duplicate_by_id_impl(self, item: MediaItem, cursor) -> bool:
        """Internal implementation of duplicate check."""
        # First check by API ID
        if item.media_type == "Anime" and item.anilist_id:
            cursor.execute('''
                SELECT COUNT(*) as count FROM media_items
                WHERE anilist_id=? AND media_type=?
            ''', (item.anilist_id, item.media_type))
            result = cursor.fetchone()
            if result['count'] > 0:
                return True
        elif item.tmdb_id:
            cursor.execute('''
                SELECT COUNT(*) as count FROM media_items
                WHERE tmdb_id=? AND media_type=?
            ''', (item.tmdb_id, item.media_type))
            result = cursor.fetchone()
            if result['count'] > 0:
                return True

        # Fallback to title+year check
        cursor.execute('''
            SELECT COUNT(*) as count FROM media_items
            WHERE title=? AND year=? AND media_type=?
        ''', (item.title, item.year, item.media_type))
        result = cursor.fetchone()
        return result['count'] > 0

    def count_items_with_quality_type(self, quality_type: str) -> int:
        """Count how many items are using a specific quality type."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM media_items
                WHERE quality_type=?
            ''', (quality_type,))
            result = cursor.fetchone()
            return result['count']
