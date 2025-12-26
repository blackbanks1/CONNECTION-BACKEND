from datetime import datetime
from functools import wraps
from flask import (
    Blueprint, request, session, jsonify,
    redirect, url_for, render_template
)
from models import db, User
from utils import normalizeRwandaNumber, validateRwandaPhone
import logging
import re  # Added

driver_auth = Blueprint("driver_auth", __name__)
logger = logging.getLogger(__name__)

# HELPERS ------------------------------------------------------

def current_user():
    """Return the currently logged-in user object or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(func):
    """Decorator to enforce login for protected routes."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user():
            if request.accept_mimetypes.accept_json:
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("driver_auth.login_page"))
        return func(*args, **kwargs)
    return wrapper

def validate_and_normalize_phone(phone):
    """Validate and normalize phone number to standard format."""
    if not phone or not isinstance(phone, str):
        return None, "Phone number is required"
    
    # Use the updated utility
    normalized = normalizeRwandaNumber(phone)
    
    if not normalized:
        return None, "Invalid Rwanda phone number. Use format: 0788 123 456"
    
    # Additional validation
    if not validateRwandaPhone(normalized):
        return None, "Invalid phone number format"
    
    # Check if phone already exists
    existing_user = User.query.filter_by(phone=normalized).first()
    if existing_user:
        return None, "Phone number already registered"
    
    return normalized, None

# HTML PAGES ---------------------------------------------------

@driver_auth.route("/login", methods=["GET"])
def login_page():
    """Render the login page."""
    return render_template("login.html")


@driver_auth.route("/signup", methods=["GET"])
def signup_page():
    """Render the signup page."""
    return render_template("signup.html")


# API ROUTES (JSON) --------------------------------------------

@driver_auth.route("/signup", methods=["POST"])  # ADDED THIS MISSING ENDPOINT!
def signup_driver():
    """API endpoint for driver signup."""
    try:
        data = request.get_json() or {}
        
        username = (data.get("username") or "").strip()
        raw_phone = (data.get("phone") or "").strip()
        password = (data.get("password") or "").strip()

        # Validate required fields
        if not username or not raw_phone or not password:
            return jsonify({"error": "All fields are required"}), 400
        
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        # NORMALIZE AND VALIDATE PHONE
        normalized_phone, error_msg = validate_and_normalize_phone(raw_phone)
        if error_msg:
            return jsonify({"error": error_msg}), 400
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already taken"}), 400
        
        # Create new user - STORE NORMALIZED PHONE
        new_user = User(
            username=username,
            phone=normalized_phone,  # STORE NORMALIZED
            role="driver",
            created_at=datetime.utcnow()
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"New driver registered: {username} ({normalized_phone})")
        
        return jsonify({
            "status": "success",
            "message": "Account created successfully",
            "user_id": new_user.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Signup error: {str(e)}")
        return jsonify({"error": "Registration failed", "details": str(e)}), 500


@driver_auth.route("/login", methods=["POST"])
def login_driver():
    """API endpoint for driver login."""
    try:
        data = request.get_json() or {}
        raw_phone = (data.get("phone") or "").strip()
        password = (data.get("password") or "").strip()

        # Validate required fields
        if not raw_phone or not password:
            return jsonify({"error": "Phone and password are required"}), 400

        # NORMALIZE phone for database lookup
        normalized = normalizeRwandaNumber(raw_phone)
        if not normalized:
            return jsonify({"error": "Invalid phone number format"}), 400

        # Look up user by NORMALIZED phone ONLY
        user = User.query.filter_by(phone=normalized).first()  # CHANGED: Only normalized
        
        if not user:
            # For security, don't reveal if phone exists or not
            return jsonify({"error": "Invalid credentials"}), 401
        
        # Validate password
        if not user.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401
        
        if user.role != "driver":
            return jsonify({"error": "Access denied. Driver account required"}), 403

        # Store user ID in session
        session["user_id"] = user.id
        
        logger.info(f"Driver logged in: {user.username} ({user.phone})")
        
        return jsonify({
            "status": "success",
            "user": {
                "id": user.id,
                "username": user.username,
                "phone": user.phone
            },
            "redirect": "/driver/home"
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed", "details": str(e)}), 500


@driver_auth.route("/logout", methods=["POST"])
def logout_driver():
    """API endpoint for driver logout."""
    user_id = session.get("user_id")
    session.pop("user_id", None)
    logger.info(f"User {user_id} logged out")
    return jsonify({"status": "logged_out"}), 200


@driver_auth.route("/home", methods=["GET"])
@login_required
def driver_home():
    """Protected driver home page."""
    return render_template("driver.html")