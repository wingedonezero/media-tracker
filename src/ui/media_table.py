"""Reusable media table widget for displaying media items."""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from typing import List
from ..database.models import MediaItem


class MediaTable(QTableWidget):
    """Table widget for displaying media items in spreadsheet format."""

    item_double_clicked = pyqtSignal(MediaItem)
    item_deleted = pyqtSignal(MediaItem)
    item_moved = pyqtSignal(MediaItem, str)  # item, new_status
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize media table."""
        super().__init__(parent)

        # Column configuration
        self.columns = ['Title', 'Year', 'Quality', 'Source', 'Notes']
        self.setColumnCount(len(self.columns))
        self.setHorizontalHeaderLabels(self.columns)

        # Table configuration
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Resize columns to content
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Year
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Quality
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Source
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Notes

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
            self.setItem(row, 0, QTableWidgetItem(item.title or ''))
            self.setItem(row, 1, QTableWidgetItem(str(item.year) if item.year else ''))
            self.setItem(row, 2, QTableWidgetItem(item.quality_type or ''))
            self.setItem(row, 3, QTableWidgetItem(item.source or ''))
            self.setItem(row, 4, QTableWidgetItem(item.notes or ''))

            # Store the item ID in the first column for easy retrieval
            self.item(row, 0).setData(Qt.ItemDataRole.UserRole, item.id)

    def get_selected_item(self) -> MediaItem:
        """Get the currently selected media item."""
        current_row = self.currentRow()
        if current_row >= 0 and current_row < len(self.media_items):
            return self.media_items[current_row]
        return None

    def _on_double_click(self, item):
        """Handle double-click event."""
        media_item = self.get_selected_item()
        if media_item:
            self.item_double_clicked.emit(media_item)

    def show_context_menu(self, position):
        """Show context menu on right-click."""
        item = self.get_selected_item()
        if not item:
            return

        menu = QMenu(self)

        # Edit action
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.item_double_clicked.emit(item))
        menu.addAction(edit_action)

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

        # Refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(lambda: self.refresh_requested.emit())
        menu.addAction(refresh_action)

        menu.exec(self.viewport().mapToGlobal(position))

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
