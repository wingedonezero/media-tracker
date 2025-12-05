"""Dialog for managing quality types."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QInputDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt
from utils.config_manager import ConfigManager
from database.db_manager import DatabaseManager


class QualityTypesDialog(QDialog):
    """Dialog for managing quality types."""

    def __init__(self, config_manager: ConfigManager, db_manager: DatabaseManager, parent=None):
        """
        Initialize quality types dialog.

        Args:
            config_manager: Configuration manager instance
            db_manager: Database manager instance for checking usage
            parent: Parent widget
        """
        super().__init__(parent)

        self.config = config_manager
        self.db = db_manager
        self.modified = False

        self.setWindowTitle("Manage Quality Types")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.setup_ui()
        self.load_quality_types()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel(
            "Manage your quality types. These will appear in the dropdown when adding/editing media items."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # List widget
        self.quality_list = QListWidget()
        layout.addWidget(self.quality_list)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Quality Type")
        self.add_button.clicked.connect(self.add_quality_type)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_quality_type)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setDefault(True)

        close_layout.addWidget(self.close_button)

        layout.addLayout(close_layout)

        self.setLayout(layout)

    def load_quality_types(self):
        """Load quality types from config into the list."""
        self.quality_list.clear()
        quality_types = sorted(self.config.get_quality_types())

        for quality_type in quality_types:
            # Check how many items are using this quality type
            count = self.db.count_items_with_quality_type(quality_type)
            if count > 0:
                display_text = f"{quality_type} (used by {count} item{'s' if count != 1 else ''})"
            else:
                display_text = quality_type

            self.quality_list.addItem(display_text)

    def add_quality_type(self):
        """Add a new quality type."""
        text, ok = QInputDialog.getText(
            self,
            "Add Quality Type",
            "Enter new quality type name:",
            text=""
        )

        if ok and text.strip():
            quality_type = text.strip()
            current_types = self.config.get_quality_types()

            if quality_type in current_types:
                QMessageBox.warning(
                    self,
                    "Duplicate",
                    f"Quality type '{quality_type}' already exists!"
                )
                return

            self.config.add_quality_type(quality_type)
            self.modified = True
            self.load_quality_types()

            QMessageBox.information(
                self,
                "Success",
                f"Quality type '{quality_type}' added successfully!"
            )

    def remove_quality_type(self):
        """Remove the selected quality type."""
        current_item = self.quality_list.currentItem()
        if not current_item:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a quality type to remove."
            )
            return

        # Extract the quality type name (remove usage count if present)
        display_text = current_item.text()
        quality_type = display_text.split(" (used by")[0]

        # Check if it's in use
        count = self.db.count_items_with_quality_type(quality_type)

        if count > 0:
            reply = QMessageBox.warning(
                self,
                "Quality Type In Use",
                f"The quality type '{quality_type}' is currently used by {count} item{'s' if count != 1 else ''}.\n\n"
                f"If you remove it, those items will no longer have a quality type assigned.\n\n"
                f"Are you sure you want to remove it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove quality type '{quality_type}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config.remove_quality_type(quality_type)
            self.modified = True
            self.load_quality_types()

            QMessageBox.information(
                self,
                "Success",
                f"Quality type '{quality_type}' removed successfully!"
            )

    def was_modified(self) -> bool:
        """Return whether quality types were modified."""
        return self.modified
