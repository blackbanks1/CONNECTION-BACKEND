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
    DSQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL").replace("postgres://", "postgresql://")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
     
    if os.environ.get("FLASK_ENV") == "production":
        PREFERRED_URL_SCHEME = "https"
    # -------------------------
    # SOCKET.IO CONFIG
    # -------------------------
    # (Already handled in app.py but kept for flexibility)
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

