#!/usr/bin/env python3
"""
Configuration loader for Cycast
Loads and validates HCL configuration files using pyhcl
"""

import os
import hcl
import logging
from typing import Dict, Any

# Get logger
logger = logging.getLogger('cycast.config')


class Config:
    """Configuration container with defaults"""
    
    DEFAULT_CONFIG = {
        'server': {
            'host': '0.0.0.0',
            'source_port': 8000,
            'listen_port': 8001,
            'source_password': 'hackme',
            'mount_point': '/stream',
        },
        'buffer': {
            'size_mb': 20,  # Increased from 10 MB
        },
        'playlist': {
            'directory': './music',
            'shuffle': True,
            'extensions': ['.mp3', '.ogg'],
        },
        'broadcaster': {
            'chunk_size': 16384,      # Increased from 8192
            'sleep_high': 0.0005,     # Reduced from 0.001
            'sleep_medium': 0.001,    # Reduced from 0.005
            'sleep_low': 0.002,       # Reduced from 0.01
        },
        'metadata': {
            'station_name': 'Cycast Radio',
            'station_description': 'High-performance internet radio',
            'station_genre': 'Various',
            'station_url': 'http://localhost:8001',
            'enable_icy': True,
            'icy_metaint': 16000,
        },
        'advanced': {
            'max_listeners': 0,
            'source_timeout': 10.0,
            'verbose_logging': False,
            'enable_stats': True,
            'flask_debug': False,
            'flask_secret_key': 'change-me-in-production',
        }
    }
    
    def __init__(self, config_file: str = 'config.hcl'):
        """Load configuration from HCL file"""
        self.config_file = config_file
        self.data = self._load_config()
    
    def _merge_config(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two configuration dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse HCL configuration file"""
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_file, 'r') as f:
                parsed = hcl.load(f)
            
            # Merge with defaults
            config = self._merge_config(self.DEFAULT_CONFIG, parsed)
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading config file {self.config_file}: {e}")
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()
    
    def get(self, section: str, key: str = None, default=None):
        """Get configuration value"""
        if key is None:
            return self.data.get(section, {})
        return self.data.get(section, {}).get(key, default)
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        # Check required fields
        if not self.get('server', 'source_password'):
            errors.append("server.source_password is required")
        
        if self.get('server', 'source_password') == 'hackme':
            logger.warning(" Using default password 'hackme' - change this in production!")
        
        if self.get('advanced', 'flask_secret_key') == 'change-me-in-production':
            logger.warning(" Using default Flask secret key - change this in production!")
        
        # Check ports
        source_port = self.get('server', 'source_port')
        listen_port = self.get('server', 'listen_port')
        
        if not (1 <= source_port <= 65535):
            errors.append(f"Invalid source_port: {source_port}")
        
        if not (1 <= listen_port <= 65535):
            errors.append(f"Invalid listen_port: {listen_port}")
        
        if source_port == listen_port:
            errors.append("source_port and listen_port must be different")
        
        # Check buffer size
        buffer_size = self.get('buffer', 'size_mb')
        if buffer_size < 1 or buffer_size > 1000:
            errors.append(f"buffer.size_mb should be between 1 and 1000, got {buffer_size}")
        
        # Check playlist directory
        playlist_dir = self.get('playlist', 'directory')
        if not os.path.exists(playlist_dir):
            logger.warning(f"Playlist directory {playlist_dir} does not exist")
        
        if errors:
            logger.error("Configuration errors:")
            for error in errors:
                logger.error(f"  {error}")
            return False
        
        return True
    
    def __repr__(self):
        """String representation of config"""
        lines = ["Cycast Configuration:"]
        for section, values in self.data.items():
            lines.append(f"  [{section}]")
            for key, value in values.items():
                lines.append(f"    {key} = {value}")
        return "\n".join(lines)


def load_config(config_file: str = 'config.hcl') -> Config:
    """Load and validate configuration"""
    config = Config(config_file)
    if not config.validate():
        raise ValueError("Invalid configuration")
    return config


if __name__ == '__main__':
    # Test configuration loading
    config = load_config()
    print(config)
