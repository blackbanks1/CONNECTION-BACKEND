import os

class Config:
    # -------------------------
    # GENERAL APP CONFIG
    # -------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # -------------------------
    # DATABASE CONFIG
    # -------------------------
    # Use PostgreSQL in production, SQLite locally
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://")

    SQLALCHEMY_DATABASE_URI = db_url or "sqlite:///local.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -------------------------
    # FORCE HTTPS IN PRODUCTION
    # -------------------------
    if os.environ.get("FLASK_ENV") == "production":
        PREFERRED_URL_SCHEME = "https"

    # -------------------------
    # SOCKET.IO CONFIG
    # -------------------------
    CORS_ALLOWED_ORIGINS = "*"

    # -------------------------
    # OPENROUTESERVICE API KEY
    # -------------------------
    ORS_API_KEY = os.getenv("ORS_API_KEY")

    # -------------------------
    # TRIAL PERIOD SETTINGS
    # -------------------------
    DRIVER_FREE_TRIAL_DAYS = int(os.getenv("DRIVER_FREE_TRIAL_DAYS", 7))

    # -------------------------
    # PAYMENT & PRICING (future)
    # -------------------------
    DAILY_PASS_PRICE_RWF = int(os.getenv("DAILY_PASS_PRICE_RWF", 500))
