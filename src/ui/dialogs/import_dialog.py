"""Import dialog for smart Excel/ODS import."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QMessageBox, QGroupBox, QCheckBox, QTextEdit, QSplitter, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from pathlib import Path
from typing import List
from utils.import_service import BaseImportService, ImportResult
from database.models import MediaItem


class ImportThread(QThread):
    """Thread for running import in background."""
    progress_updated = pyqtSignal(int, int, str)  # current, total, entry
    result_ready = pyqtSignal(object)  # individual ImportResult as it's processed
    import_finished = pyqtSignal()  # signals completion (no data needed, already have results)
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
                progress_callback=self.progress_callback,
                result_callback=self.result_callback
            )
            self.import_finished.emit()
        except Exception as e:
            self.import_error.emit(str(e))

    def progress_callback(self, current, total, entry):
        """Progress callback."""
        self.progress_updated.emit(current, total, entry)

    def result_callback(self, result):
        """Result callback - called for each processed entry."""
        self.result_ready.emit(result)


class ImportDialog(QDialog):
    """Dialog for importing media from Excel/ODS files with smart matching."""

    def __init__(self, parent, db_manager, import_service: BaseImportService):
        """
        Initialize import dialog.

        Args:
            parent: Parent widget
            db_manager: Database manager
            import_service: Import service instance (Anime, Movie, or TV)
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.import_service = import_service
        self.import_results: List[ImportResult] = []
        self.import_thread = None
        self.import_in_progress = False  # Track if import is currently running

        # Get media type from service
        self.media_type = import_service.get_media_type()

        # Set window title based on media type
        self.setWindowTitle(f"Smart Import - {self.media_type}")
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

        # Tree controls
        tree_controls = QHBoxLayout()

        select_all_btn = QPushButton("Select All Successful")
        select_all_btn.clicked.connect(self.select_all_successful)
        select_all_btn.setToolTip("Select all new (non-duplicate) matches")
        tree_controls.addWidget(select_all_btn)

        expand_all_btn = QPushButton("Expand All")
        expand_all_btn.clicked.connect(lambda: self.results_tree.expandAll())
        tree_controls.addWidget(expand_all_btn)

        collapse_all_btn = QPushButton("Collapse All")
        collapse_all_btn.clicked.connect(lambda: self.results_tree.collapseAll())
        tree_controls.addWidget(collapse_all_btn)

        tree_controls.addStretch()
        results_layout.addLayout(tree_controls)

        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels([
            "Status", "Original Entry", "Parsed Title", "Matches", "Confidence"
        ])
        self.results_tree.setColumnWidth(0, 100)
        self.results_tree.setColumnWidth(1, 300)
        self.results_tree.setColumnWidth(2, 200)
        self.results_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.results_tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.results_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
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

        # Status selector for adding items
        actions_layout.addWidget(QLabel("Add to:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["On Drive", "To Download", "To Work On"])
        self.status_combo.setCurrentText("To Download")
        self.status_combo.setMinimumWidth(150)
        actions_layout.addWidget(self.status_combo)

        actions_layout.addWidget(QLabel("|"))

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

        # Mark import as in progress (prevents manual matching during import)
        self.import_in_progress = True

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
        self.import_thread.result_ready.connect(self.on_result_ready)  # NEW: incremental results
        self.import_thread.import_finished.connect(self.on_import_finished)
        self.import_thread.import_error.connect(self.on_import_error)
        self.import_thread.start()

    def on_progress_updated(self, current, total, entry):
        """Update progress bar."""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Processing {current}/{total}: {entry}...")

    def on_result_ready(self, result: ImportResult):
        """Handle individual result as it's processed (incremental display)."""
        # Add to results list
        self.import_results.append(result)

        # Add to tree immediately
        self.add_result_to_tree(result, len(self.import_results) - 1)

        # Update statistics incrementally
        self.update_statistics(self.import_results)

    def on_import_finished(self):
        """Handle import completion."""
        self.import_in_progress = False  # Import complete, allow manual matching
        self.status_label.setText("Import complete! Double-click unmatched items to manually search.")
        self.progress_bar.setValue(100)

        # Enable buttons
        self.import_button.setEnabled(True)
        self.add_all_button.setEnabled(True)
        self.add_selected_button.setEnabled(True)
        self.export_unmatched_button.setEnabled(True)

    def on_import_error(self, error_message):
        """Handle import error."""
        self.import_in_progress = False  # Import failed, allow manual matching
        self.status_label.setText(f"Error: {error_message}")
        self.import_button.setEnabled(True)
        QMessageBox.critical(self, "Import Error", f"Failed to import:\n{error_message}")

    def add_result_to_tree(self, result: ImportResult, result_index: int):
        """Add a single result to the tree (for incremental display)."""
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

        # Store result index in item
        item.setData(0, Qt.ItemDataRole.UserRole, result_index)

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

        # Add to tree and expand
        self.results_tree.addTopLevelItem(item)
        item.setExpanded(True)

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
            f"Add {len(items_to_add)} {self.media_type.lower()} item(s) to the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            added_count = self.add_matches_to_db(items_to_add)
            QMessageBox.information(self, "Success", f"Added {added_count} {self.media_type.lower()} item(s) to database!")

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
        QMessageBox.information(self, "Success", f"Added {added_count} {self.media_type.lower()} item(s) to database!")

        # Refresh results
        self.populate_results_tree(self.import_results)

    def add_matches_to_db(self, matches: List[dict]) -> int:
        """
        Add matches to database with TRANSACTION SAFETY.
        Returns count of added items.

        CRITICAL SAFEGUARDS:
        1. Each item wrapped in try/except to prevent cascading failures
        2. Uses correct ID field based on media type (anilist_id, tmdb_id)
        3. Marks items as added in session to prevent duplicates
        4. Only adds items that passed duplicate check
        """
        added_count = 0
        added_ids = []

        # Get selected status from combo box
        selected_status = self.status_combo.currentText()

        # Get the correct ID field name for this media type
        id_field_name = self.import_service.get_id_field_name()

        for match in matches:
            try:
                # Build kwargs for MediaItem, using the correct ID field
                item_kwargs = {
                    'title': match.get('title'),
                    'year': match.get('year'),
                    'media_type': self.media_type,
                    'status': selected_status,
                    'poster_url': match.get('poster_url')
                }

                # Add the correct ID field (anilist_id for Anime, tmdb_id for Movie/TV)
                match_id = self.import_service.get_match_id(match)
                if match_id:
                    item_kwargs[id_field_name] = match_id

                # For anime, also add native_title and romaji_title
                if self.media_type == 'Anime':
                    item_kwargs['native_title'] = match.get('native_title')
                    item_kwargs['romaji_title'] = match.get('romaji_title')

                media_item = MediaItem(**item_kwargs)

                self.db_manager.add_item(media_item)
                added_count += 1
                if match_id:
                    added_ids.append(match_id)
            except Exception as e:
                print(f"Failed to add {match.get('title')}: {e}")

        # Mark as added in import session to prevent duplicate searches
        # This is a CRITICAL SAFEGUARD against duplicates within the same import
        if added_ids:
            self.import_service.mark_as_added(added_ids)

        return added_count

    def select_all_successful(self):
        """Select all successful (non-duplicate) matches in the tree."""
        self.results_tree.clearSelection()

        for i in range(self.results_tree.topLevelItemCount()):
            parent = self.results_tree.topLevelItem(i)

            # Iterate through child matches
            for j in range(parent.childCount()):
                child = parent.child(j)

                # Check if this is a non-duplicate match
                match = child.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(match, dict):
                    is_dup, _ = self.import_service.check_duplicate(match)
                    if not is_dup:
                        child.setSelected(True)

        # Show count
        selected_count = len(self.results_tree.selectedItems())
        if selected_count > 0:
            QMessageBox.information(
                self,
                "Selection",
                f"Selected {selected_count} new matches.\n\n"
                "Tip: Use Ctrl+Click to deselect individual items, or "
                "Shift+Click to select ranges."
            )
        else:
            QMessageBox.information(
                self,
                "No Matches",
                "No new matches to select (all are duplicates or no results)."
            )

    def export_unmatched(self):
        """Export unmatched entries to a text file."""
        unmatched = [
            result for result in self.import_results
            if result.status in ['no_match', 'error']
        ]

        if not unmatched:
            QMessageBox.information(self, "No Unmatched", "No unmatched entries to export!")
            return

        default_filename = f"unmatched_{self.media_type.lower()}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Unmatched Entries",
            str(Path.home() / default_filename),
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Unmatched {self.media_type} Entries ({len(unmatched)} total)\n")
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

    def on_item_double_clicked(self, item, column):
        """
        Handle double-click on tree item.
        Allow manual matching for unmatched entries (only when import is complete).
        """
        # CRITICAL SAFEGUARD: Don't allow editing while import is in progress
        if self.import_in_progress:
            QMessageBox.warning(
                self,
                "Import In Progress",
                "Please wait for the import to complete before manually matching items."
            )
            return

        # Only allow manual matching on top-level items (not child matches)
        if item.parent():
            return

        # Get the result index from the item
        result_index = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(result_index, int) or result_index >= len(self.import_results):
            return

        result = self.import_results[result_index]

        # Only allow manual matching for unmatched or error items
        if result.status not in ['no_match', 'error']:
            return

        # Open manual match dialog
        self.open_manual_match_dialog(result, result_index)

    def open_manual_match_dialog(self, result: ImportResult, result_index: int):
        """Open manual match dialog for an unmatched result."""
        from ui.dialogs.manual_match_dialog import ManualMatchDialog

        dialog = ManualMatchDialog(
            parent=self,
            import_service=self.import_service,
            original_text=result.original_text,
            parsed_titles=result.parsed_titles
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_matches = dialog.get_selected_matches()

            if selected_matches:
                # Update the ImportResult with manually selected matches
                result.matches = selected_matches

                # Calculate confidence for best match
                if selected_matches:
                    result.confidence = max(m.get('_confidence', 0) for m in selected_matches)

                # Check for duplicates
                duplicate_matches = []
                new_matches = []

                for match in selected_matches:
                    is_dup, dup_desc = self.import_service.check_duplicate(match)
                    if is_dup:
                        duplicate_matches.append((match, dup_desc))
                    else:
                        new_matches.append(match)

                # Update status
                if duplicate_matches and not new_matches:
                    result.status = 'duplicate'
                    result.message = f"All {len(duplicate_matches)} manually matched item(s) already in database"
                elif duplicate_matches and new_matches:
                    result.status = 'partial_duplicate'
                    result.message = f"Found {len(new_matches)} new match(es), {len(duplicate_matches)} duplicate(s) [manual]"
                else:
                    result.status = 'success'
                    result.message = f"Found {len(new_matches)} match(es) [manual]"

                # Refresh the tree to show updated result
                self.populate_results_tree(self.import_results)

                # Update statistics
                self.update_statistics(self.import_results)

                QMessageBox.information(
                    self,
                    "Matches Added",
                    f"Successfully added {len(selected_matches)} match(es) to this entry.\n\n"
                    "The entry is now shown with the updated matches."
                )
