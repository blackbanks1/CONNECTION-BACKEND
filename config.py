"""
Configuration settings for Connection delivery tracking system
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///connection.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application
    APP_NAME = "Connection Delivery Tracker"
    VERSION = "1.0.0"
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    
    # Phone validation
    DEFAULT_COUNTRY_CODE = '250'
    PHONE_NUMBER_LENGTH = 12  # 250XXXXXXXXX
    
    # Delivery
    MAX_ACTIVE_DELIVERIES = 3
    SESSION_TIMEOUT_MINUTES = 30
    
    # Maps
    DEFAULT_MAP_CENTER = [-1.9706, 30.1044]  # Kigali, Rwanda
    DEFAULT_ZOOM_LEVEL = 12
    
    # Real-time updates
    LOCATION_UPDATE_INTERVAL = 5  # seconds
    MAX_LOCATION_HISTORY = 100
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '*').split(',')
    
    # Subscription & Pricing
    TESTING_MODE = os.environ.get('TESTING_MODE', 'true').lower() == 'true'
    DRIVER_FREE_TRIAL_DAYS = int(os.environ.get('DRIVER_FREE_TRIAL_DAYS', 7))
    DAILY_PASS_PRICE_RWF = int(os.environ.get('DAILY_PASS_PRICE_RWF', 500))
    
    # GraphHopper API
    GRAPHHOPPER_KEY = os.environ.get('GRAPHHOPPER_KEY', '')
    
    # Server
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False  # Disable in development

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific settings
    REQUIRE_SUBSCRIPTION = os.environ.get('REQUIRE_SUBSCRIPTION', 'true').lower() == 'true'
    TRIAL_END_NOTIFICATION_DAYS = int(os.environ.get('TRIAL_END_NOTIFICATION_DAYS', 3))

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SESSION_COOKIE_SECURE = False

# Rwanda bounding box coordinates (approximate)
RWANDA_BOUNDS = {
    'min_lat': -2.84,
    'max_lat': -1.05,
    'min_lon': 28.86,
    'max_lon': 30.90
}

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development').lower()
    return config.get(config_name, config['default'])