from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Blueprint,
    request,
    session,
    jsonify,
    redirect,
    url_for
)

from models import db, User

driver_auth = Blueprint("driver_auth", __name__)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def current_user():
    """Return the logged in user or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(func):
    """Decorator to protect views."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("driver_auth.login_page"))
        return func(*args, **kwargs)
    return wrapper


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@driver_auth.route("/driver/signup", methods=["POST"])
def signup_driver():
    data = request.get_json() or {}

    phone = data.get("phone")
    password = data.get("password")
    name = data.get("name")

    if not phone or not password:
        return jsonify({"error": "missing_fields"}), 400

    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "phone_exists"}), 409

    new_user = User(
        name=name,
        phone=phone,
        password=User.hash_password(password),
        created_at=datetime.utcnow()
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"status": "success"}), 201


@driver_auth.route("/driver/login", methods=["POST"])
def login_driver():
    data = request.get_json() or {}

    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return jsonify({"error": "missing_fields"}), 400

    driver = User.query.filter_by(phone=phone).first()

    if not driver or not driver.check_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    session["user_id"] = driver.id
    session.permanent = True

    return jsonify({"status": "success"}), 200


@driver_auth.route("/driver/logout", methods=["POST"])
def logout_driver():
    session.pop("user_id", None)
    return jsonify({"status": "logged_out"}), 200


# --------------------------------------------------
# PAGES (HTML)
# --------------------------------------------------

@driver_auth.route("/driver/login")
def login_page():
    """Serves the login page driver.html expects to redirect to."""
    return redirect("/templates/driver_login.html")  # or your actual path


@driver_auth.route("/driver/home")
@login_required
def driver_home():
    """Redirects to driver.html after login."""
    return redirect("/driver.html")
