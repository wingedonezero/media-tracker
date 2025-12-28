"""Import dialog for smart Excel/ODS import."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QMessageBox, QGroupBox, QCheckBox, QTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from pathlib import Path
from typing import List
from utils.import_service import SmartImportService, ImportResult
from database.models import MediaItem


class ImportThread(QThread):
    """Thread for running import in background."""
    progress_updated = pyqtSignal(int, int, str)  # current, total, entry
    import_finished = pyqtSignal(list)  # results
    import_error = pyqtSignal(str)  # error message

    def __init__(self, import_service, file_path):
        super().__init__()
        self.import_service = import_service
        self.file_path = file_path

    def run(self):
        """Run import process."""
        try:
            results = self.import_service.import_file(
                self.file_path,
                progress_callback=self.progress_callback
            )
            self.import_finished.emit(results)
        except Exception as e:
            self.import_error.emit(str(e))

    def progress_callback(self, current, total, entry):
        """Progress callback."""
        self.progress_updated.emit(current, total, entry)


class ImportDialog(QDialog):
    """Dialog for importing anime from Excel/ODS files."""

    def __init__(self, parent, db_manager, anilist_client):
        super().__init__(parent)
        self.db_manager = db_manager
        self.anilist_client = anilist_client
        self.import_service = SmartImportService(anilist_client, db_manager)
        self.import_results: List[ImportResult] = []
        self.import_thread = None

        self.setWindowTitle("Smart Import - Anime")
        self.setModal(True)
        self.resize(1000, 700)

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # File selection
        file_group = QGroupBox("1. Select File")
        file_layout = QHBoxLayout()
        file_group.setLayout(file_layout)

        self.file_label = QLabel("No file selected")
        file_layout.addWidget(self.file_label)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_button)

        self.import_button = QPushButton("Start Import")
        self.import_button.clicked.connect(self.start_import)
        self.import_button.setEnabled(False)
        file_layout.addWidget(self.import_button)

        layout.addWidget(file_group)

        # Progress
        progress_group = QGroupBox("2. Import Progress")
        progress_layout = QVBoxLayout()
        progress_group.setLayout(progress_layout)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to import")
        progress_layout.addWidget(self.status_label)

        layout.addWidget(progress_group)

        # Results
        results_group = QGroupBox("3. Results")
        results_layout = QVBoxLayout()
        results_group.setLayout(results_layout)

        # Splitter for tree and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels([
            "Status", "Original Entry", "Parsed Title", "Matches", "Confidence"
        ])
        self.results_tree.setColumnWidth(0, 100)
        self.results_tree.setColumnWidth(1, 300)
        self.results_tree.setColumnWidth(2, 200)
        self.results_tree.itemSelectionChanged.connect(self.on_selection_changed)
        splitter.addWidget(self.results_tree)

        # Details panel
        details_widget = QGroupBox("Match Details")
        details_layout = QVBoxLayout()
        details_widget.setLayout(details_layout)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)

        splitter.addWidget(details_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        results_layout.addWidget(splitter)

        # Statistics
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        results_layout.addLayout(stats_layout)

        layout.addWidget(results_group)

        # Actions
        actions_layout = QHBoxLayout()

        self.add_all_button = QPushButton("Add All Successful Matches")
        self.add_all_button.clicked.connect(self.add_all_matches)
        self.add_all_button.setEnabled(False)
        actions_layout.addWidget(self.add_all_button)

        self.add_selected_button = QPushButton("Add Selected")
        self.add_selected_button.clicked.connect(self.add_selected_matches)
        self.add_selected_button.setEnabled(False)
        actions_layout.addWidget(self.add_selected_button)

        self.export_unmatched_button = QPushButton("Export Unmatched")
        self.export_unmatched_button.clicked.connect(self.export_unmatched)
        self.export_unmatched_button.setEnabled(False)
        actions_layout.addWidget(self.export_unmatched_button)

        actions_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        actions_layout.addWidget(close_button)

        layout.addLayout(actions_layout)

    def browse_file(self):
        """Browse for import file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Import File",
            str(Path.home()),
            "Spreadsheet Files (*.ods *.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            self.file_label.setText(Path(file_path).name)
            self.file_path = file_path
            self.import_button.setEnabled(True)

    def start_import(self):
        """Start the import process."""
        if not hasattr(self, 'file_path'):
            return

        # Disable buttons
        self.import_button.setEnabled(False)
        self.add_all_button.setEnabled(False)
        self.add_selected_button.setEnabled(False)
        self.export_unmatched_button.setEnabled(False)

        # Clear results
        self.results_tree.clear()
        self.details_text.clear()
        self.import_results = []
        self.progress_bar.setValue(0)

        # Start import thread
        self.import_thread = ImportThread(self.import_service, self.file_path)
        self.import_thread.progress_updated.connect(self.on_progress_updated)
        self.import_thread.import_finished.connect(self.on_import_finished)
        self.import_thread.import_error.connect(self.on_import_error)
        self.import_thread.start()

    def on_progress_updated(self, current, total, entry):
        """Update progress bar."""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Processing {current}/{total}: {entry}...")

    def on_import_finished(self, results: List[ImportResult]):
        """Handle import completion."""
        self.import_results = results
        self.status_label.setText("Import complete!")
        self.progress_bar.setValue(100)

        # Populate results tree
        self.populate_results_tree(results)

        # Update statistics
        self.update_statistics(results)

        # Enable buttons
        self.import_button.setEnabled(True)
        self.add_all_button.setEnabled(True)
        self.add_selected_button.setEnabled(True)
        self.export_unmatched_button.setEnabled(True)

    def on_import_error(self, error_message):
        """Handle import error."""
        self.status_label.setText(f"Error: {error_message}")
        self.import_button.setEnabled(True)
        QMessageBox.critical(self, "Import Error", f"Failed to import:\n{error_message}")

    def populate_results_tree(self, results: List[ImportResult]):
        """Populate the results tree."""
        self.results_tree.clear()

        for i, result in enumerate(results):
            # Create top-level item
            item = QTreeWidgetItem()

            # Status column with color
            status_text = result.status.replace('_', ' ').title()
            item.setText(0, status_text)

            # Color code by status
            if result.status == 'success':
                item.setBackground(0, QBrush(QColor(200, 255, 200)))  # Light green
            elif result.status == 'partial_duplicate':
                item.setBackground(0, QBrush(QColor(255, 255, 200)))  # Light yellow
            elif result.status == 'duplicate':
                item.setBackground(0, QBrush(QColor(255, 230, 200)))  # Light orange
            elif result.status == 'no_match':
                item.setBackground(0, QBrush(QColor(255, 200, 200)))  # Light red
            elif result.status == 'error':
                item.setBackground(0, QBrush(QColor(255, 180, 180)))  # Red

            # Original entry (truncated)
            original_short = result.original_text[:80] + "..." if len(result.original_text) > 80 else result.original_text
            item.setText(1, original_short)

            # Parsed title
            parsed_title = result.parsed_titles.get('english') or result.parsed_titles.get('romaji') or result.parsed_titles.get('japanese', '')
            item.setText(2, parsed_title)

            # Number of matches
            item.setText(3, str(len(result.matches)))

            # Confidence
            if result.confidence > 0:
                item.setText(4, f"{result.confidence:.0%}")

            # Store result in item
            item.setData(0, Qt.ItemDataRole.UserRole, i)

            # Add match children
            for match in result.matches:
                child = QTreeWidgetItem()
                match_title = match.get('title', 'Unknown')
                match_year = match.get('year', 'N/A')
                confidence = match.get('_confidence', 0)

                child.setText(0, "Match")
                child.setText(1, f"{match_title} ({match_year})")
                child.setText(2, match.get('romaji_title', ''))
                child.setText(3, "")
                child.setText(4, f"{confidence:.0%}")

                # Store match data
                child.setData(0, Qt.ItemDataRole.UserRole, match)

                # Check if duplicate
                is_dup, dup_desc = self.import_service.check_duplicate(match)
                if is_dup:
                    child.setBackground(0, QBrush(QColor(255, 200, 200)))
                    child.setText(0, "Duplicate")
                    child.setToolTip(1, f"Already in database: {dup_desc}")

                item.addChild(child)

            self.results_tree.addTopLevelItem(item)

        # Expand all items
        self.results_tree.expandAll()

    def update_statistics(self, results: List[ImportResult]):
        """Update statistics label."""
        total = len(results)
        success = sum(1 for r in results if r.status == 'success')
        partial = sum(1 for r in results if r.status == 'partial_duplicate')
        duplicate = sum(1 for r in results if r.status == 'duplicate')
        no_match = sum(1 for r in results if r.status == 'no_match')
        error = sum(1 for r in results if r.status == 'error')

        stats_text = (
            f"Total: {total} | "
            f"✓ Success: {success} | "
            f"⚠ Partial: {partial} | "
            f"= Duplicate: {duplicate} | "
            f"✗ No Match: {no_match} | "
            f"⊗ Error: {error}"
        )
        self.stats_label.setText(stats_text)

    def on_selection_changed(self):
        """Handle tree selection change."""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            self.details_text.clear()
            return

        item = selected_items[0]

        # Check if it's a match item (child) or result item (parent)
        if item.parent():  # It's a match
            match = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(match, dict):
                self.show_match_details(match)
        else:  # It's a result
            result_index = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(result_index, int) and result_index < len(self.import_results):
                result = self.import_results[result_index]
                self.show_result_details(result)

    def show_match_details(self, match: dict):
        """Show details for a match."""
        details = []
        details.append(f"<h3>{match.get('title', 'Unknown')}</h3>")
        details.append(f"<b>Year:</b> {match.get('year', 'N/A')}<br>")
        details.append(f"<b>Romaji:</b> {match.get('romaji_title', 'N/A')}<br>")
        details.append(f"<b>Native:</b> {match.get('native_title', 'N/A')}<br>")
        details.append(f"<b>AniList ID:</b> {match.get('id', 'N/A')}<br>")
        details.append(f"<b>Confidence:</b> {match.get('_confidence', 0):.0%}<br>")

        if match.get('overview'):
            details.append(f"<br><b>Description:</b><br>{match['overview'][:300]}...")

        # Check if duplicate
        is_dup, dup_desc = self.import_service.check_duplicate(match)
        if is_dup:
            details.append(f"<br><b><span style='color: red;'>⚠ Already in database:</span></b> {dup_desc}")

        self.details_text.setHtml("".join(details))

    def show_result_details(self, result: ImportResult):
        """Show details for a result."""
        details = []
        details.append(f"<h3>Import Entry</h3>")
        details.append(f"<b>Status:</b> {result.status.replace('_', ' ').title()}<br>")
        details.append(f"<b>Message:</b> {result.message}<br>")
        details.append(f"<br><b>Original Entry:</b><br>{result.original_text[:500]}<br>")
        details.append(f"<br><b>Parsed Titles:</b><br>")
        for key, value in result.parsed_titles.items():
            if value:
                details.append(f"  - {key.title()}: {value}<br>")

        self.details_text.setHtml("".join(details))

    def add_all_matches(self):
        """Add all successful matches to database."""
        if not self.import_results:
            return

        items_to_add = []

        for result in self.import_results:
            if result.status not in ['success', 'partial_duplicate']:
                continue

            for match in result.matches:
                # Skip duplicates
                is_dup, _ = self.import_service.check_duplicate(match)
                if is_dup:
                    continue

                items_to_add.append(match)

        if not items_to_add:
            QMessageBox.information(self, "No Items", "No new items to add (all are duplicates or failed matches).")
            return

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Add",
            f"Add {len(items_to_add)} anime to the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            added_count = self.add_matches_to_db(items_to_add)
            QMessageBox.information(self, "Success", f"Added {added_count} anime to database!")

            # Refresh results to show new duplicates
            self.populate_results_tree(self.import_results)

    def add_selected_matches(self):
        """Add selected matches to database."""
        selected_items = self.results_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select matches to add.")
            return

        items_to_add = []

        for item in selected_items:
            # Only process match items (children)
            if item.parent():
                match = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(match, dict):
                    # Skip duplicates
                    is_dup, _ = self.import_service.check_duplicate(match)
                    if not is_dup:
                        items_to_add.append(match)

        if not items_to_add:
            QMessageBox.information(self, "No Items", "No new items to add (selected items are duplicates).")
            return

        added_count = self.add_matches_to_db(items_to_add)
        QMessageBox.information(self, "Success", f"Added {added_count} anime to database!")

        # Refresh results
        self.populate_results_tree(self.import_results)

    def add_matches_to_db(self, matches: List[dict]) -> int:
        """Add matches to database. Returns count of added items."""
        added_count = 0
        added_ids = []

        for match in matches:
            try:
                media_item = MediaItem(
                    title=match.get('title'),
                    native_title=match.get('native_title'),
                    romaji_title=match.get('romaji_title'),
                    year=match.get('year'),
                    media_type='Anime',
                    status='To Download',
                    anilist_id=match.get('id'),
                    poster_url=match.get('poster_url')
                )

                self.db_manager.add_item(media_item)
                added_count += 1
                added_ids.append(match.get('id'))
            except Exception as e:
                print(f"Failed to add {match.get('title')}: {e}")

        # Mark as added in import session to prevent duplicate searches
        if added_ids:
            self.import_service.mark_as_added(added_ids)

        return added_count

    def export_unmatched(self):
        """Export unmatched entries to a text file."""
        unmatched = [
            result for result in self.import_results
            if result.status in ['no_match', 'error']
        ]

        if not unmatched:
            QMessageBox.information(self, "No Unmatched", "No unmatched entries to export!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Unmatched Entries",
            str(Path.home() / "unmatched_anime.txt"),
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Unmatched Anime Entries ({len(unmatched)} total)\n")
                    f.write("=" * 80 + "\n\n")

                    for i, result in enumerate(unmatched, 1):
                        f.write(f"{i}. {result.original_text}\n")
                        f.write(f"   Status: {result.status}\n")
                        f.write(f"   Message: {result.message}\n")
                        f.write(f"   Parsed titles: {result.parsed_titles}\n")
                        f.write("\n")

                QMessageBox.information(self, "Success", f"Exported {len(unmatched)} unmatched entries to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
