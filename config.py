import os

class Config:
    # -------------------------
    # ENVIRONMENT
    # -------------------------
    ENV = os.getenv("FLASK_ENV", "development")
    TESTING_MODE = os.getenv("TESTING_MODE", "false").lower() == "true"

    # -------------------------
    # GENERAL APP CONFIG
    # -------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    if ENV == "production" and JWT_SECRET_KEY == "dev-jwt-secret":
        raise RuntimeError("JWT_SECRET_KEY must be set in production")

    # -------------------------
    # DATABASE CONFIG
    # -------------------------
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://")

    SQLALCHEMY_DATABASE_URI = db_url or "sqlite:///local.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 5
    }

    # -------------------------
    # FORCE HTTPS IN PRODUCTION
    # -------------------------
    if ENV == "production":
        PREFERRED_URL_SCHEME = "https"

    # -------------------------
    # SOCKET.IO CONFIG
    # -------------------------
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    ]

    # -------------------------
    # ROUTING API KEYS
    # -------------------------
    GRAPHHOPPER_KEY = os.getenv("GRAPHHOPPER_KEY", "dev-graphhopper-key")
    if ENV == "production" and GRAPHHOPPER_KEY == "dev-graphhopper-key":
        raise RuntimeError("GRAPHHOPPER_KEY must be set in production")

    # -------------------------
    # TRIAL PERIOD SETTINGS
    # -------------------------
    DRIVER_FREE_TRIAL_DAYS = int(os.getenv("DRIVER_FREE_TRIAL_DAYS", 7))

    # -------------------------
    # PAYMENT & PRICING (future)
    # -------------------------
    DAILY_PASS_PRICE_RWF = int(os.getenv("DAILY_PASS_PRICE_RWF", 500))

    # -------------------------
    # JWT cookie support
    # -------------------------
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = ENV == "production"
    JWT_COOKIE_CSRF_PROTECT = ENV == "production"