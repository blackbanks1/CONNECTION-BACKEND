from datetime import datetime
from functools import wraps
from flask import (
    Blueprint, request, session, jsonify,
    redirect, url_for, render_template
)
from models import db, User
from  utils import normalizeRwandaNumber  # make sure you have this helper
import logging
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
            # Return JSON for API clients, redirect for HTML pages
            if request.accept_mimetypes.accept_json:
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("driver_auth.login_page"))
        return func(*args, **kwargs)
    return wrapper


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
@driver_auth.route("/signup", methods=["POST"])
def signup_api():
    """API endpoint to create a new user account."""
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    phone = (data.get("phone") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or None)  # optional now

    # Validate required fields
    if not phone or not password:
        return jsonify({"error": "missing_fields", "message": "Phone and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "weak_password", "message": "Password must be at least 6 characters"}), 400

    # Check uniqueness
    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "phone_exists", "message": "Phone number already registered"}), 409
    if username and User.query.filter_by(username=username).first():
        return jsonify({"error": "username_exists", "message": "Username already taken"}), 409
    if email and User.query.filter_by(email=email).first():
        return jsonify({"error": "email_exists", "message": "Email already registered"}), 409

    # Create new user
    user = User(
        username=username or phone,
        phone=phone,
        email=email,
        created_at=datetime.utcnow()
    )
    try:
        user.set_password(password)  # hashes securely
    except ValueError as ve:
        return jsonify({"error": "weak_password", "message": str(ve)}), 400

    if hasattr(user, "start_trial"):
        user.start_trial()

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Signup DB error: {e}")
        return jsonify({"error": "db_error", "message": "Internal server error"}), 500

    return jsonify({"status": "success", "message": "Account created successfully"}), 201
# LOGIN / LOGOUT / HOME ----------------------------------------



@driver_auth.route("/login", methods=["POST"])
def login_driver():
    """API endpoint for driver login."""
    try:
        data = request.get_json() or {}

        phone = data.get("phone")
        password = data.get("password")

        # Validate required fields
        if not phone or not password:
            return jsonify({"error": "phone_and_password_required"}), 400

        # Normalize phone before lookup
        normalized = normalizeRwandaNumber(phone)
        if not normalized:
            return jsonify({"error": "invalid_phone_format"}), 400

        # Look up user by normalized phone
        user = User.query.filter_by(phone=normalized).first()

        # Validate credentials
        if not user or not user.check_password(password):
            return jsonify({"error": "invalid_credentials"}), 401

        # Store user ID in session (requires app.secret_key configured)
        session["user_id"] = user.id

        return jsonify({"status": "success"}), 200

    except Exception as e:
        # Catch all unexpected errors
        db.session.rollback()
        return jsonify({"error": "internal_server_error", "details": str(e)}), 500

@driver_auth.route("/logout", methods=["POST"])
def logout_driver():
    """API endpoint for driver logout."""
    session.pop("user_id", None)
    return jsonify({"status": "logged_out"}), 200


@driver_auth.route("/home", methods=["GET"])
@login_required
def driver_home():
    """Protected driver home page."""
    return render_template("driver.html")