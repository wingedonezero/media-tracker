"""Main application window."""

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QToolBar, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from ui.media_table import MediaTable
from ui.dialogs.edit_dialog import EditDialog
from ui.dialogs.quality_types_dialog import QualityTypesDialog
from ui.dialogs.import_dialog import ImportDialog
from ui.settings_dialog import SettingsDialog
from database.db_manager import DatabaseManager
from database.models import MediaItem
from api.tmdb_client import TMDBClient
from api.anilist_client import AniListClient
from utils.config_manager import ConfigManager


class MainWindow(QMainWindow):
    """Main application window with tabs and tables."""

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        # Initialize config manager
        self.config = ConfigManager()

        self.setWindowTitle("Media Tracker")

        # Load window size from config
        width = self.config.get('window_width', 1200)
        height = self.config.get('window_height', 700)
        self.setGeometry(100, 100, width, height)

        # Initialize database and API clients
        self.db = DatabaseManager()

        # Initialize TMDB client and load API key from config
        self.tmdb_client = TMDBClient()
        saved_api_key = self.config.get('tmdb_api_key', '')
        if saved_api_key:
            self.tmdb_client.api_key = saved_api_key

        self.anilist_client = AniListClient()

        # Store current media type and status
        self.current_media_type = "Movie"
        self.current_status = "On Drive"

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Toolbar
        self.create_toolbar()

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title or notes...")
        self.search_input.textChanged.connect(self.search_items)
        search_layout.addWidget(self.search_input)

        self.clear_search_button = QPushButton("Clear")
        self.clear_search_button.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_button)

        main_layout.addLayout(search_layout)

        # Main tabs (Movies, TV Shows, Anime)
        self.main_tabs = QTabWidget()
        self.main_tabs.currentChanged.connect(self.on_main_tab_changed)

        # Create tabs for each media type
        self.movie_tab = self.create_media_type_tab("Movie")
        self.tv_tab = self.create_media_type_tab("TV")
        self.anime_tab = self.create_media_type_tab("Anime")

        self.main_tabs.addTab(self.movie_tab, "Movies")
        self.main_tabs.addTab(self.tv_tab, "TV Shows")
        self.main_tabs.addTab(self.anime_tab, "Anime")

        main_layout.addWidget(self.main_tabs)

        # Status bar
        self.statusBar().showMessage("Ready")

    def create_toolbar(self):
        """Create application toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add button
        add_action = QAction("Add Item", self)
        add_action.triggered.connect(self.add_item)
        toolbar.addAction(add_action)

        # Import button (for Anime only)
        import_action = QAction("Import Anime", self)
        import_action.triggered.connect(self.import_anime)
        toolbar.addAction(import_action)

        toolbar.addSeparator()

        # Refresh button
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.load_data)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # TMDB API Key button
        tmdb_action = QAction("TMDB API Key", self)
        tmdb_action.triggered.connect(self.configure_tmdb)
        toolbar.addAction(tmdb_action)

        # Quality Types button
        quality_types_action = QAction("Quality Types", self)
        quality_types_action.triggered.connect(self.manage_quality_types)
        toolbar.addAction(quality_types_action)

        # Settings button
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

    def create_media_type_tab(self, media_type: str) -> QWidget:
        """Create a tab with sub-tabs for a media type."""
        tab_widget = QWidget()
        layout = QVBoxLayout()
        tab_widget.setLayout(layout)

        # Sub-tabs for status
        sub_tabs = QTabWidget()

        # Get saved row height from config
        saved_row_height = self.config.get('row_height', 80)

        # Create table for each status
        for status in ["On Drive", "To Download", "To Work On"]:
            table = MediaTable()
            table.item_double_clicked.connect(self.edit_item)
            table.item_deleted.connect(self.delete_item)
            table.item_moved.connect(self.move_item)
            table.refresh_requested.connect(self.load_data)

            # Apply saved row height
            table.set_row_height(saved_row_height)

            # Store reference to table
            setattr(self, f"{media_type.lower().replace(' ', '_')}_{status.lower().replace(' ', '_')}_table", table)

            sub_tabs.addTab(table, status)

        layout.addWidget(sub_tabs)

        # Store reference to sub-tabs BEFORE connecting signals
        setattr(self, f"{media_type.lower().replace(' ', '_')}_sub_tabs", sub_tabs)

        # Connect signal AFTER storing the reference
        sub_tabs.currentChanged.connect(lambda: self.on_sub_tab_changed(media_type))

        return tab_widget

    def on_main_tab_changed(self, index):
        """Handle main tab change."""
        media_types = ["Movie", "TV", "Anime"]
        if 0 <= index < len(media_types):
            self.current_media_type = media_types[index]
            self.update_current_status()
            self.update_status_bar()

    def on_sub_tab_changed(self, media_type: str):
        """Handle sub-tab change."""
        if media_type == self.current_media_type:
            self.update_current_status()
            self.update_status_bar()

    def update_current_status(self):
        """Update the current status based on selected sub-tab."""
        sub_tabs = getattr(self, f"{self.current_media_type.lower().replace(' ', '_')}_sub_tabs")
        statuses = ["On Drive", "To Download", "To Work On"]
        current_index = sub_tabs.currentIndex()
        if 0 <= current_index < len(statuses):
            self.current_status = statuses[current_index]

    def get_current_table(self) -> MediaTable:
        """Get the currently visible table."""
        table_name = f"{self.current_media_type.lower().replace(' ', '_')}_{self.current_status.lower().replace(' ', '_')}_table"
        return getattr(self, table_name)

    def load_data(self):
        """Load data from database into all tables."""
        for media_type in ["Movie", "TV", "Anime"]:
            for status in ["On Drive", "To Download", "To Work On"]:
                table_name = f"{media_type.lower().replace(' ', '_')}_{status.lower().replace(' ', '_')}_table"
                table = getattr(self, table_name)

                items = self.db.get_items(media_type=media_type, status=status)
                table.load_items(items)

        self.update_status_bar()

    def add_item(self):
        """Add a new media item (or multiple items via multi-select)."""
        dialog = EditDialog(
            self.current_media_type,
            tmdb_client=self.tmdb_client,
            anilist_client=self.anilist_client,
            config_manager=self.config,
            parent=self
        )

        # Set default status to current tab
        dialog.status_combo.setCurrentText(self.current_status)

        if dialog.exec():
            # Check if multiple items were selected
            selected_items = dialog.get_selected_items()

            if selected_items:
                # Multi-select mode: batch add with transaction safety
                try:
                    result = self.db.add_items_batch(selected_items, skip_duplicates=True)

                    # Show detailed feedback
                    message_parts = []
                    if result['added'] > 0:
                        message_parts.append(f"✓ Added {result['added']} item(s)")
                    if result['skipped'] > 0:
                        message_parts.append(f"⊘ Skipped {result['skipped']} duplicate(s)")
                    if result['errors'] > 0:
                        message_parts.append(f"✗ {result['errors']} error(s)")

                    message = "\n".join(message_parts)

                    if result['added'] > 0:
                        self.load_data()

                    # Show detailed results dialog
                    details = []
                    if result['added_items']:
                        details.append("Added:\n  • " + "\n  • ".join(result['added_items']))
                    if result['skipped_items']:
                        details.append("\nSkipped (duplicates):\n  • " + "\n  • ".join(result['skipped_items']))

                    QMessageBox.information(
                        self,
                        "Multi-Select Results",
                        message + "\n\n" + "\n".join(details)
                    )

                    # Status bar message
                    if result['added'] > 0:
                        self.statusBar().showMessage(
                            f"Added {result['added']} items ({result['skipped']} skipped)",
                            5000
                        )

                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to add items:\n{str(e)}\n\nNo items were added (transaction rolled back)."
                    )

            else:
                # Single item mode
                item = dialog.get_item()

                # Check for duplicates
                if self.db.check_duplicate(item.title, item.year, item.media_type):
                    reply = QMessageBox.question(
                        self,
                        'Duplicate Found',
                        f'"{item.title}" ({item.year}) already exists. Add anyway?',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        return

                self.db.add_item(item)
                self.load_data()
                self.statusBar().showMessage(f"Added: {item.title}", 3000)

    def import_anime(self):
        """Import anime from Excel/ODS file."""
        dialog = ImportDialog(
            parent=self,
            db_manager=self.db,
            anilist_client=self.anilist_client
        )

        dialog.exec()

        # Reload data after import
        self.load_data()

    def edit_item(self, item: MediaItem):
        """Edit an existing media item."""
        dialog = EditDialog(
            item.media_type,
            item=item,
            tmdb_client=self.tmdb_client,
            anilist_client=self.anilist_client,
            config_manager=self.config,
            parent=self
        )

        if dialog.exec():
            updated_item = dialog.get_item()
            self.db.update_item(updated_item)
            self.load_data()
            self.statusBar().showMessage(f"Updated: {updated_item.title}", 3000)

    def delete_item(self, item: MediaItem):
        """Delete a media item."""
        self.db.delete_item(item.id)
        self.load_data()
        self.statusBar().showMessage(f"Deleted: {item.title}", 3000)

    def move_item(self, item: MediaItem, new_status: str):
        """Move item to a different status category."""
        item.status = new_status
        self.db.update_item(item)
        self.load_data()
        self.statusBar().showMessage(f"Moved '{item.title}' to {new_status}", 3000)

    def search_items(self):
        """Search for items in current media type."""
        search_term = self.search_input.text().strip()

        if not search_term:
            self.load_data()
            return

        # Search in current media type
        results = self.db.search_items(search_term, media_type=self.current_media_type)

        # Group results by status
        for status in ["On Drive", "To Download", "To Work On"]:
            table_name = f"{self.current_media_type.lower().replace(' ', '_')}_{status.lower().replace(' ', '_')}_table"
            table = getattr(self, table_name)

            status_items = [item for item in results if item.status == status]
            table.load_items(status_items)

        self.update_status_bar()

    def clear_search(self):
        """Clear search and reload all data."""
        self.search_input.clear()
        self.load_data()

    def configure_tmdb(self):
        """Configure TMDB API key."""
        current_key = self.tmdb_client.api_key or ""

        api_key, ok = QInputDialog.getText(
            self,
            "TMDB API Key",
            "Enter your TMDB API key:\n\n"
            "Get a free key at:\nhttps://www.themoviedb.org/settings/api\n\n"
            "API Key:",
            text=current_key
        )

        if ok and api_key.strip():
            self.tmdb_client.api_key = api_key.strip()
            self.config.set('tmdb_api_key', api_key.strip())
            QMessageBox.information(self, "Success", "TMDB API key configured!")

    def open_settings(self):
        """Open settings dialog."""
        # Get current row height from config
        current_height = self.config.get('row_height', 80)

        dialog = SettingsDialog(current_row_height=current_height, parent=self)

        if dialog.exec():
            new_height = dialog.get_row_height()

            # Save to config
            self.config.set('row_height', new_height)

            # Update all tables with new row height
            for media_type in ["Movie", "TV", "Anime"]:
                for status in ["On Drive", "To Download", "To Work On"]:
                    table_name = f"{media_type.lower().replace(' ', '_')}_{status.lower().replace(' ', '_')}_table"
                    table = getattr(self, table_name)
                    table.set_row_height(new_height)

            QMessageBox.information(self, "Settings Saved", f"Row height set to {new_height}px")

    def manage_quality_types(self):
        """Open quality types management dialog."""
        dialog = QualityTypesDialog(
            config_manager=self.config,
            db_manager=self.db,
            parent=self
        )

        dialog.exec()

        # If quality types were modified, show a message
        if dialog.was_modified():
            QMessageBox.information(
                self,
                "Quality Types Updated",
                "Quality types have been updated. The changes will be reflected "
                "when you add or edit items."
            )

    def update_status_bar(self):
        """Update status bar with current stats."""
        table = self.get_current_table()
        count = table.rowCount()
        self.statusBar().showMessage(
            f"{self.current_media_type} - {self.current_status}: {count} items"
        )

    def closeEvent(self, event):
        """Handle window close event to save settings."""
        # Save window size
        self.config.set('window_width', self.width())
        self.config.set('window_height', self.height())
        event.accept()
