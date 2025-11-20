# config.py
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///connection.db")

class Config:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ORS_API_KEY = os.getenv("ORS_API_KEY", None)
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32))
