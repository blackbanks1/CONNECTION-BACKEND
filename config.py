import os

class Config:
    # -------------------------
    # GENERAL APP CONFIG
    # -------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

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
    if os.environ.get("FLASK_ENV") == "production":
        PREFERRED_URL_SCHEME = "https"

    # -------------------------
    # SOCKET.IO CONFIG
    # -------------------------
    CORS_ALLOWED_ORIGINS = "*"

    # -------------------------
    # ROUTING API KEYS
    # -------------------------
    ORS_API_KEY = os.getenv("ORS_API_KEY")

    # ✅ ADD THIS LINE (Your real GraphHopper Key)
    GRAPHHOPPER_KEY = os.getenv(
        "GRAPHHOPPER_KEY",
        "27764287-a135-45e3-95a1-e0a8aa7569e2"
    )

    # -------------------------
    # TRIAL PERIOD SETTINGS
    # -------------------------
    DRIVER_FREE_TRIAL_DAYS = int(os.getenv("DRIVER_FREE_TRIAL_DAYS", 7))

    # -------------------------
    # PAYMENT & PRICING (future)
    # -------------------------
    DAILY_PASS_PRICE_RWF = int(os.getenv("DAILY_PASS_PRICE_RWF", 500))
