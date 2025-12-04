"""Settings dialog for application preferences."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox,
    QPushButton, QHBoxLayout, QGroupBox, QLabel
)


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    def __init__(self, current_row_height: int = 80, parent=None):
        """Initialize settings dialog."""
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)

        self.setup_ui(current_row_height)

    def setup_ui(self, current_row_height: int):
        """Set up the user interface."""
        layout = QVBoxLayout()

        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QFormLayout()

        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(30, 200)
        self.row_height_spin.setValue(current_row_height)
        self.row_height_spin.setSuffix(" px")
        display_layout.addRow("Row Height:", self.row_height_spin)

        help_label = QLabel("Adjust row height to show more/less of poster images.")
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        display_layout.addRow("", help_label)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

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

    def get_row_height(self) -> int:
        """Get the selected row height."""
        return self.row_height_spin.value()
