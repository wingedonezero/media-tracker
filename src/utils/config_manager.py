"""Configuration manager for saving and loading application settings."""

import json
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    """Manages application configuration settings."""

    def __init__(self, config_file: str = "data/config.json"):
        """Initialize config manager."""
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                return self.get_defaults()
        return self.get_defaults()

    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a configuration value and save."""
        self.config[key] = value
        self.save()

    @staticmethod
    def get_defaults() -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'row_height': 80,
            'tmdb_api_key': '',
            'window_width': 1200,
            'window_height': 700,
            'quality_types': [
                "BluRay",
                "BluRay 1080p",
                "BluRay 2160p",
                "Remux",
                "Remux 1080p",
                "Remux 2160p",
                "WEB-DL 1080p",
                "WEB-DL 2160p",
                "WebDL"
            ]
        }

    def get_quality_types(self) -> list:
        """Get the list of quality types."""
        return self.get('quality_types', self.get_defaults()['quality_types'])

    def add_quality_type(self, quality_type: str):
        """Add a new quality type."""
        quality_types = self.get_quality_types()
        if quality_type not in quality_types:
            quality_types.append(quality_type)
            self.set('quality_types', quality_types)

    def remove_quality_type(self, quality_type: str):
        """Remove a quality type."""
        quality_types = self.get_quality_types()
        if quality_type in quality_types:
            quality_types.remove(quality_type)
            self.set('quality_types', quality_types)
