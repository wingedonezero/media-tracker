"""Reusable media table widget for displaying media items."""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox, QLabel, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from typing import List
from database.models import MediaItem
from utils.image_loader import ImageLoader


class MediaTable(QTableWidget):
    """Table widget for displaying media items in spreadsheet format."""

    item_double_clicked = pyqtSignal(MediaItem)
    item_deleted = pyqtSignal(MediaItem)
    item_moved = pyqtSignal(MediaItem, str)  # item, new_status
    items_bulk_deleted = pyqtSignal(list)  # list of items
    items_bulk_moved = pyqtSignal(list, str)  # list of items, new_status
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize media table."""
        super().__init__(parent)

        # Image loader
        self.image_loader = ImageLoader()

        # Row height setting (can be changed via settings)
        self.row_height = 80

        # Column configuration
        self.columns = ['Poster', 'Title', 'Year', 'Quality', 'Source', 'Notes']
        self.setColumnCount(len(self.columns))
        self.setHorizontalHeaderLabels(self.columns)

        # Table configuration
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)  # Enable multi-select
        self.setSortingEnabled(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Resize columns to content
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Poster
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Year
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Quality
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Source
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Notes
        self.setColumnWidth(0, 60)  # Fixed width for poster column

        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Double-click to edit
        self.itemDoubleClicked.connect(self._on_double_click)

        # Store media items
        self.media_items: List[MediaItem] = []

    def load_items(self, items: List[MediaItem]):
        """Load media items into the table."""
        self.media_items = items
        self.setRowCount(len(items))

        for row, item in enumerate(items):
            # Set row height
            self.setRowHeight(row, self.row_height)

            # Poster image (column 0)
            poster_label = QLabel()
            poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if item.poster_url:
                pixmap = self.image_loader.load_image(
                    item.poster_url,
                    max_width=50,
                    max_height=self.row_height - 10
                )
                if not pixmap.isNull():
                    poster_label.setPixmap(pixmap)
            self.setCellWidget(row, 0, poster_label)

            # Text columns
            self.setItem(row, 1, QTableWidgetItem(item.title or ''))
            self.setItem(row, 2, QTableWidgetItem(str(item.year) if item.year else ''))
            self.setItem(row, 3, QTableWidgetItem(item.quality_type or ''))
            self.setItem(row, 4, QTableWidgetItem(item.source or ''))
            self.setItem(row, 5, QTableWidgetItem(item.notes or ''))

            # Store the item ID in the title column for easy retrieval
            self.item(row, 1).setData(Qt.ItemDataRole.UserRole, item.id)

    def set_row_height(self, height: int):
        """Set the row height for all rows."""
        self.row_height = height
        for row in range(self.rowCount()):
            self.setRowHeight(row, height)

    def get_selected_item(self) -> MediaItem:
        """Get the currently selected media item."""
        current_row = self.currentRow()
        if current_row >= 0 and current_row < len(self.media_items):
            return self.media_items[current_row]
        return None

    def get_selected_items(self) -> List[MediaItem]:
        """Get all currently selected media items."""
        selected_rows = set(index.row() for index in self.selectedIndexes())
        selected_items = []
        for row in sorted(selected_rows):
            if row >= 0 and row < len(self.media_items):
                selected_items.append(self.media_items[row])
        return selected_items

    def _on_double_click(self, item):
        """Handle double-click event."""
        media_item = self.get_selected_item()
        if media_item:
            self.item_double_clicked.emit(media_item)

    def show_context_menu(self, position):
        """Show context menu on right-click."""
        selected_items = self.get_selected_items()
        if not selected_items:
            return

        menu = QMenu(self)
        is_multi_select = len(selected_items) > 1

        if is_multi_select:
            # Multi-select context menu
            menu.addAction(QAction(f"{len(selected_items)} items selected", self)).setEnabled(False)
            menu.addSeparator()

            # Move to submenu
            move_menu = menu.addMenu("Move all to")
            statuses = ["On Drive", "To Download", "To Work On"]
            for status in statuses:
                # Only show statuses that differ from at least one selected item
                if any(item.status != status for item in selected_items):
                    action = QAction(status, self)
                    action.triggered.connect(lambda checked, s=status: self.items_bulk_moved.emit(selected_items, s))
                    move_menu.addAction(action)

            menu.addSeparator()

            # Delete all action
            delete_action = QAction("Delete all", self)
            delete_action.triggered.connect(lambda: self._confirm_bulk_delete(selected_items))
            menu.addAction(delete_action)

        else:
            # Single-select context menu (original behavior)
            item = selected_items[0]

            # Edit action
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.item_double_clicked.emit(item))
            menu.addAction(edit_action)

            menu.addSeparator()

            # Copy name action(s)
            if item.media_type == "Anime":
                # For anime, show submenu with all title types
                copy_menu = menu.addMenu("Copy Name")

                if item.title:
                    copy_english = QAction(f"English: {item.title[:30]}...", self) if len(item.title) > 30 else QAction(f"English: {item.title}", self)
                    copy_english.triggered.connect(lambda: self._copy_to_clipboard(item.title))
                    copy_menu.addAction(copy_english)

                if item.romaji_title:
                    copy_romaji = QAction(f"Romaji: {item.romaji_title[:30]}...", self) if len(item.romaji_title) > 30 else QAction(f"Romaji: {item.romaji_title}", self)
                    copy_romaji.triggered.connect(lambda: self._copy_to_clipboard(item.romaji_title))
                    copy_menu.addAction(copy_romaji)

                if item.native_title:
                    copy_native = QAction(f"Japanese: {item.native_title[:30]}...", self) if len(item.native_title) > 30 else QAction(f"Japanese: {item.native_title}", self)
                    copy_native.triggered.connect(lambda: self._copy_to_clipboard(item.native_title))
                    copy_menu.addAction(copy_native)
            else:
                # For movies/TV, just copy the title directly
                copy_action = QAction("Copy Name", self)
                copy_action.triggered.connect(lambda: self._copy_to_clipboard(item.title))
                menu.addAction(copy_action)

            menu.addSeparator()

            # Move to submenu
            move_menu = menu.addMenu("Move to")

            statuses = ["On Drive", "To Download", "To Work On"]
            for status in statuses:
                if status != item.status:
                    action = QAction(status, self)
                    action.triggered.connect(lambda checked, s=status: self.item_moved.emit(item, s))
                    move_menu.addAction(action)

            menu.addSeparator()

            # Delete action
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self._confirm_delete(item))
            menu.addAction(delete_action)

        menu.addSeparator()

        # Refresh action (always available)
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(lambda: self.refresh_requested.emit())
        menu.addAction(refresh_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _confirm_delete(self, item: MediaItem):
        """Confirm before deleting an item."""
        reply = QMessageBox.question(
            self,
            'Confirm Delete',
            f'Are you sure you want to delete "{item.title}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.item_deleted.emit(item)

    def _confirm_bulk_delete(self, items: List[MediaItem]):
        """Confirm before deleting multiple items."""
        titles_preview = "\n".join([f"• {item.title}" for item in items[:10]])
        if len(items) > 10:
            titles_preview += f"\n... and {len(items) - 10} more"

        reply = QMessageBox.question(
            self,
            'Confirm Bulk Delete',
            f'Are you sure you want to delete {len(items)} items?\n\n{titles_preview}',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.items_bulk_deleted.emit(items)
