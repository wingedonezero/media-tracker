"""Main entry point for Media Tracker application."""

import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Initialize and run the application."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Media Tracker")
    app.setOrganizationName("MediaTracker")
    app.setApplicationVersion("1.0.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
