import os
import json
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Default config path
CONFIG_PATH = 'config.json'

# Load configuration
def load_config():
    """
    Load configuration from JSON file
    Falls back to default values if file not found
    """
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {CONFIG_PATH}")
                return config
        else:
            logger.warning(f"Configuration file {CONFIG_PATH} not found, using defaults")
            return get_default_config()
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return get_default_config()

# Default configuration
def get_default_config():
    """
    Return default configuration values
    Used as fallback if config file is missing or invalid
    """
    return {
        "app": {
            "name": "Social Media Platform",
            "description": "A Facebook-like social media platform with advanced features",
            "version": "1.0.0"
        },
        "site": {
            "site_name": "SocialConnect",
            "domain": "socialconnect.replit.app",
            "logo_path": "/static/images/logo.svg",
            "favicon_path": "/static/images/favicon.ico",
            "theme": "dark",
            "colors": {
                "primary": "#1877f2",
                "secondary": "#42b72a",
                "background": "#18191a",
                "surface": "#242526",
                "text": "#e4e6eb"
            }
        },
        "features": {
            "max_photos_per_post": 5,
            "story_duration_hours": 24,
            "max_video_duration_seconds": 60,
            "max_friend_count": 1000,
            "max_group_members": 100,
            "min_group_members": 3
        },
        "upload": {
            "image_services": [
                "imgur",
                "catbox",
                "gofile",
                "pixhost",
                "0x0"
            ],
            "preferred_services": ["imgur", "catbox"],
            "rate_limit_seconds": 1,
            "max_retries": 3,
            "retry_delay_seconds": 2,
            "allowed_image_extensions": ["jpg", "jpeg", "png", "gif"],
            "allowed_video_extensions": ["mp4", "webm", "ogg"],
            "max_upload_size_bytes": 16777216
        },
        "firebase": {
            "config_path": "static/js/firebase-config.js",
            "auth_enabled": True,
            "auth_methods": ["email", "google", "facebook"]
        },
        "messaging": {
            "mqtt_enabled": True,
            "websocket_fallback": True,
            "read_receipts_enabled": True,
            "typing_indicators_enabled": True,
            "message_unsend_timeout_minutes": 10,
            "emoji_shortcuts_enabled": True
        },
        "development": {
            "debug_enabled": True,
            "log_level": "DEBUG",
            "auto_reload": True,
            "local_storage_fallback": True,
            "dummy_data_enabled": False
        }
    }

# Get configuration by key
def get_config(key=None, default=None):
    """
    Get configuration value by key
    Supports nested keys with dot notation (e.g., 'app.name')
    Returns entire config if key is None
    Returns default if key not found
    """
    config = load_config()
    if key is None:
        return config
    
    # Handle nested keys with dot notation
    parts = key.split('.')
    value = config
    try:
        for part in parts:
            value = value[part]
        return value
    except (KeyError, TypeError):
        logger.warning(f"Configuration key '{key}' not found, using default: {default}")
        return default

# Initialize configuration
config = load_config()

# Helper functions for common config values
def get_app_name():
    return get_config('app.name', 'Social Media Platform')

def get_site_name():
    return get_config('site.name', 'SocialConnect')

def get_upload_services():
    return get_config('upload.image_services', [])

def get_allowed_image_extensions():
    return get_config('upload.allowed_image_extensions', ["jpg", "jpeg", "png", "gif"])

def get_allowed_video_extensions():
    return get_config('upload.allowed_video_extensions', ["mp4", "webm", "ogg"])

def get_max_upload_size():
    return get_config('upload.max_upload_size_bytes', 16 * 1024 * 1024)

def is_debug_enabled():
    return get_config('development.debug_enabled', True)

def is_firebase_auth_enabled():
    return get_config('firebase.auth_enabled', True)