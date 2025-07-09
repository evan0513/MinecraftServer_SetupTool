"""
Configuration management for Minecraft Server Installer
"""

import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_file = Path.home() / ".minecraft_server_installer_config.json"
        self.default_config = {
            "language": "en",
            "theme": "dark",
            "max_versions": 50,
            "window_size": "900x700"
        }
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file, create with defaults if doesn't exist"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value and save"""
        self.config[key] = value
        self.save_config()
    
    def update(self, updates):
        """Update multiple configuration values and save"""
        self.config.update(updates)
        self.save_config()