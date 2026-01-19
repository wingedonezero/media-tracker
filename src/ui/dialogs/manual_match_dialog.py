"""Manual match dialog for fixing unmatched import results."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QHeaderView
)
from PyQt6.QtCore import Qt
from typing import List, Dict, Optional
from utils.import_service import BaseImportService


class ManualMatchDialog(QDialog):
    """Dialog for manually searching and matching unmatched import entries."""

    def __init__(self, parent, import_service: BaseImportService, original_text: str, parsed_titles: Dict[str, str]):
        """
        Initialize manual match dialog.

        Args:
            parent: Parent widget
            import_service: Import service to use for searching
            original_text: Original import entry text
            parsed_titles: Parsed titles from the entry
        """
        super().__init__(parent)
        self.import_service = import_service
        self.original_text = original_text
        self.parsed_titles = parsed_titles
        self.selected_matches: List[Dict] = []

        media_type = import_service.get_media_type()
        self.setWindowTitle(f"Manual Match - {media_type}")
        self.setModal(True)
        self.resize(800, 600)

        self.setup_ui()
        self.populate_search_field()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Original entry info
        info_group = QGroupBox("Original Entry")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)

        self.original_label = QLabel(f"Text: {self.original_text[:200]}...")
        self.original_label.setWordWrap(True)
        info_layout.addWidget(self.original_label)

        layout.addWidget(info_group)

        # Search section
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout()
        search_group.setLayout(search_layout)

        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel("Search for:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.returnPressed.connect(self.search)
        search_input_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search)
        search_input_layout.addWidget(self.search_button)

        search_layout.addLayout(search_input_layout)

        # Year input (optional)
        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("Year (optional):"))
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("YYYY")
        self.year_input.setMaximumWidth(100)
        year_layout.addWidget(self.year_input)
        year_layout.addStretch()
        search_layout.addLayout(year_layout)

        layout.addWidget(search_group)

        # Results section
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        results_group.setLayout(results_layout)

        self.status_label = QLabel("Enter a search term and click 'Search'")
        results_layout.addWidget(self.status_label)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Title", "Year", "Confidence", "Status"])
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.results_table.horizontalHeader().setStretchLastSection(False)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        results_layout.addWidget(self.results_table)

        layout.addWidget(results_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.add_button = QPushButton("Add Selected Matches")
        self.add_button.clicked.connect(self.accept_matches)
        self.add_button.setEnabled(False)
        button_layout.addWidget(self.add_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def populate_search_field(self):
        """Pre-populate search field with best available title."""
        # Try to use the best parsed title as default
        title = (
            self.parsed_titles.get('title') or
            self.parsed_titles.get('english') or
            self.parsed_titles.get('romaji') or
            self.parsed_titles.get('japanese') or
            ''
        )
        self.search_input.setText(title)

        # Pre-populate year if available
        year = self.parsed_titles.get('year', '')
        if year:
            self.year_input.setText(str(year))

    def search(self):
        """Perform search using import service."""
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Empty Search", "Please enter a search term.")
            return

        # Disable search while searching
        self.search_button.setEnabled(False)
        self.status_label.setText("Searching...")
        self.results_table.setRowCount(0)

        try:
            # Build titles dict for search
            titles = {'title': search_term}

            # Add year if provided
            year_text = self.year_input.text().strip()
            if year_text and year_text.isdigit():
                titles['year'] = year_text

            # Use import service to search
            matches, was_cached = self.import_service.search_media(titles)

            if not matches:
                self.status_label.setText("No matches found. Try a different search term.")
                return

            # Calculate confidence for each match
            for match in matches:
                match['_confidence'] = self.import_service.calculate_confidence(titles, match)

            # Sort by confidence
            matches.sort(key=lambda x: x.get('_confidence', 0), reverse=True)

            # Populate results table
            self.results_table.setRowCount(len(matches))
            for i, match in enumerate(matches):
                # Store match data in row
                self.results_table.setItem(i, 0, QTableWidgetItem(match.get('title', 'Unknown')))
                self.results_table.setItem(i, 1, QTableWidgetItem(str(match.get('year', 'N/A'))))

                confidence = match.get('_confidence', 0)
                self.results_table.setItem(i, 2, QTableWidgetItem(f"{confidence:.0%}"))

                # Check if duplicate
                is_dup, dup_desc = self.import_service.check_duplicate(match)
                status = "Duplicate" if is_dup else "New"
                status_item = QTableWidgetItem(status)
                if is_dup:
                    status_item.setToolTip(f"Already in database: {dup_desc}")
                self.results_table.setItem(i, 3, status_item)

                # Store match object in first column
                self.results_table.item(i, 0).setData(Qt.ItemDataRole.UserRole, match)

            self.status_label.setText(f"Found {len(matches)} match(es). Select one or more to add.")
            self.add_button.setEnabled(True)

        except Exception as e:
            self.status_label.setText(f"Search error: {e}")
            QMessageBox.critical(self, "Search Error", f"Failed to search:\n{e}")

        finally:
            self.search_button.setEnabled(True)

    def accept_matches(self):
        """Accept selected matches and close dialog."""
        selected_rows = set(item.row() for item in self.results_table.selectedItems())

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one match to add.")
            return

        # Collect selected matches
        self.selected_matches = []
        for row in sorted(selected_rows):
            match = self.results_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if match:
                self.selected_matches.append(match)

        if self.selected_matches:
            self.accept()
        else:
            QMessageBox.warning(self, "No Matches", "No valid matches selected.")

    def get_selected_matches(self) -> List[Dict]:
        """Get the selected matches."""
        return self.selected_matches
