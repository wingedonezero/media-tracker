"""Dialog for adding and editing media items."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QSpinBox, QComboBox, QTextEdit, QPushButton,
    QLabel, QListWidget, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from database.models import MediaItem
from api.tmdb_client import TMDBClient
from api.anilist_client import AniListClient
from utils.image_loader import ImageLoader
from utils.config_manager import ConfigManager


class EditDialog(QDialog):
    """Dialog for editing or creating media items."""

    def __init__(self, media_type: str, item: MediaItem = None,
                 tmdb_client: TMDBClient = None, anilist_client: AniListClient = None,
                 config_manager: ConfigManager = None, parent=None):
        """
        Initialize edit dialog.

        Args:
            media_type: Type of media (TV/Movie/Anime)
            item: Existing item to edit, or None for new item
            tmdb_client: TMDB API client
            anilist_client: AniList API client
            config_manager: Configuration manager for quality types
        """
        super().__init__(parent)

        self.media_type = media_type
        self.item = item or MediaItem(media_type=media_type)
        self.tmdb_client = tmdb_client
        self.anilist_client = anilist_client
        self.config = config_manager
        self.search_results = []
        self.image_loader = ImageLoader()

        # Timer for auto-search as you type
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_online)

        self.setWindowTitle(f"{'Edit' if item else 'Add'} {media_type}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(550)

        self.setup_ui()
        self.load_item_data()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Search section (only for new items)
        if not self.item.id:
            search_group = QGroupBox("Search Online Database")
            search_layout = QVBoxLayout()

            search_input_layout = QHBoxLayout()
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("Start typing to search...")
            self.search_input.textChanged.connect(self.on_search_text_changed)
            self.search_input.returnPressed.connect(self.search_online)

            self.search_button = QPushButton("Search")
            self.search_button.clicked.connect(self.search_online)

            search_input_layout.addWidget(self.search_input)
            search_input_layout.addWidget(self.search_button)

            self.search_results_list = QListWidget()
            self.search_results_list.setMaximumHeight(150)
            self.search_results_list.itemDoubleClicked.connect(self.select_search_result)

            search_layout.addLayout(search_input_layout)
            search_layout.addWidget(QLabel("Results appear as you type. Double-click to select:"))
            search_layout.addWidget(self.search_results_list)

            search_group.setLayout(search_layout)
            layout.addWidget(search_group)

        # Main content layout (poster on left, form on right)
        content_layout = QHBoxLayout()

        # Poster display
        poster_container = QVBoxLayout()
        self.poster_label = QLabel()
        self.poster_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_label.setMinimumSize(150, 225)
        self.poster_label.setMaximumSize(150, 225)
        self.poster_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        poster_container.addWidget(QLabel("Poster:"))
        poster_container.addWidget(self.poster_label)
        poster_container.addStretch()
        content_layout.addLayout(poster_container)

        # Form fields
        form_group = QGroupBox("Details")
        form_layout = QFormLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter title...")
        form_layout.addRow("Title:", self.title_input)

        # Native and Romaji title fields (for anime only)
        if self.media_type == "Anime":
            self.native_title_input = QLineEdit()
            self.native_title_input.setPlaceholderText("Japanese title...")
            self.native_title_input.setReadOnly(True)  # Auto-filled from API
            form_layout.addRow("Japanese Title:", self.native_title_input)

            self.romaji_title_input = QLineEdit()
            self.romaji_title_input.setPlaceholderText("Romaji title...")
            self.romaji_title_input.setReadOnly(True)  # Auto-filled from API
            form_layout.addRow("Romaji Title:", self.romaji_title_input)
        else:
            self.native_title_input = None
            self.romaji_title_input = None

        self.year_input = QSpinBox()
        self.year_input.setRange(1900, 2100)
        self.year_input.setValue(2024)
        self.year_input.setSpecialValueText("Unknown")
        form_layout.addRow("Year:", self.year_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["On Drive", "To Download", "To Work On"])
        form_layout.addRow("Status:", self.status_combo)

        self.quality_combo = QComboBox()
        self.quality_combo.setEditable(True)
        # Load quality types from config
        if self.config:
            quality_types = [""] + sorted(self.config.get_quality_types())
        else:
            # Fallback to defaults if config not provided
            quality_types = [
                "", "Remux", "WebDL", "BluRay", "WEB-DL 1080p", "WEB-DL 2160p",
                "Remux 1080p", "Remux 2160p", "BluRay 1080p", "BluRay 2160p"
            ]
            quality_types = [""] + sorted(quality_types[1:])  # Sort the defaults too
        self.quality_combo.addItems(quality_types)
        form_layout.addRow("Quality Type:", self.quality_combo)

        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("e.g., Torrent, Usenet, etc.")
        form_layout.addRow("Source:", self.source_input)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.notes_input.setPlaceholderText("Additional notes...")
        form_layout.addRow("Notes:", self.notes_input)

        form_group.setLayout(form_layout)
        content_layout.addWidget(form_group)

        # Add content layout to main layout
        layout.addLayout(content_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setDefault(True)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_item_data(self):
        """Load existing item data into form fields."""
        if self.item.id:
            self.title_input.setText(self.item.title or '')
            if self.native_title_input and self.item.native_title:
                self.native_title_input.setText(self.item.native_title)
            if self.romaji_title_input and self.item.romaji_title:
                self.romaji_title_input.setText(self.item.romaji_title)
            if self.item.year:
                self.year_input.setValue(self.item.year)
            self.status_combo.setCurrentText(self.item.status)
            if self.item.quality_type:
                self.quality_combo.setCurrentText(self.item.quality_type)
            if self.item.source:
                self.source_input.setText(self.item.source)
            if self.item.notes:
                self.notes_input.setPlainText(self.item.notes)

        # Load poster image
        if self.item.poster_url:
            self.update_poster(self.item.poster_url)

    def update_poster(self, poster_url: str):
        """Update the poster image display."""
        if poster_url:
            pixmap = self.image_loader.load_image(poster_url, max_width=150, max_height=225)
            if not pixmap.isNull():
                self.poster_label.setPixmap(pixmap)
            else:
                self.poster_label.setText("No Image")
        else:
            self.poster_label.setText("No Poster")

    def on_search_text_changed(self):
        """Handle search text changed - trigger search after delay."""
        # Stop the current timer if running
        self.search_timer.stop()

        # Only search if there's text
        if self.search_input.text().strip():
            # Start timer for 500ms delay (search after user stops typing)
            self.search_timer.start(500)

    def search_online(self):
        """Search online database for media."""
        query = self.search_input.text().strip()
        if not query:
            return

        self.search_results_list.clear()
        self.search_results = []

        # Search based on media type
        if self.media_type == "Anime":
            if not self.anilist_client:
                QMessageBox.information(self, "Info", "AniList client not available")
                return

            self.search_button.setEnabled(False)
            self.search_button.setText("Searching...")

            results = self.anilist_client.search_anime(query)
            self.search_results = results

            for result in results:
                year_str = f" ({result['year']})" if result['year'] else ""
                native_str = f" - {result['native_title']}" if result.get('native_title') else ""
                self.search_results_list.addItem(f"{result['title']}{year_str}{native_str}")

        else:
            if not self.tmdb_client or not self.tmdb_client.api_key:
                QMessageBox.information(
                    self,
                    "Info",
                    "TMDB API key not configured. Please add your API key in the settings.\n\n"
                    "Get a free key at: https://www.themoviedb.org/settings/api"
                )
                return

            self.search_button.setEnabled(False)
            self.search_button.setText("Searching...")

            if self.media_type == "Movie":
                results = self.tmdb_client.search_movie(query)
            else:  # TV
                results = self.tmdb_client.search_tv(query)

            self.search_results = results

            for result in results:
                year_str = f" ({result['year']})" if result['year'] else ""
                self.search_results_list.addItem(f"{result['title']}{year_str}")

        self.search_button.setEnabled(True)
        self.search_button.setText("Search")

    def select_search_result(self, list_item):
        """Fill form with selected search result."""
        index = self.search_results_list.row(list_item)
        if index < 0 or index >= len(self.search_results):
            return

        result = self.search_results[index]

        self.title_input.setText(result['title'])
        if result['year']:
            try:
                self.year_input.setValue(int(result['year']))
            except (ValueError, TypeError):
                pass

        # Fill native and romaji titles for anime
        if self.native_title_input and result.get('native_title'):
            self.native_title_input.setText(result['native_title'])
        if self.romaji_title_input and result.get('romaji_title'):
            self.romaji_title_input.setText(result['romaji_title'])

        # Store API IDs
        if self.media_type == "Anime":
            self.item.anilist_id = result['id']
        else:
            self.item.tmdb_id = result['id']

        # Update poster
        if result.get('poster_url'):
            self.item.poster_url = result['poster_url']
            self.update_poster(result['poster_url'])

    def get_item(self) -> MediaItem:
        """Get the media item with form data."""
        self.item.title = self.title_input.text().strip()
        if self.native_title_input:
            self.item.native_title = self.native_title_input.text().strip() or None
        if self.romaji_title_input:
            self.item.romaji_title = self.romaji_title_input.text().strip() or None
        year = self.year_input.value()
        self.item.year = year if year > 1900 else None
        self.item.status = self.status_combo.currentText()
        self.item.quality_type = self.quality_combo.currentText().strip() or None
        self.item.source = self.source_input.text().strip() or None
        self.item.notes = self.notes_input.toPlainText().strip() or None
        self.item.media_type = self.media_type

        return self.item

    def accept(self):
        """Validate and accept the dialog."""
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Title is required!")
            return

        super().accept()
