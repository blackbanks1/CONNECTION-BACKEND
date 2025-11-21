from datetime import datetime
from functools import wraps
from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template
from models import db, User

driver_auth = Blueprint("driver_auth", __name__)


# HELPERS ------------------------------------------------------

def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("driver_auth.login_page"))
        return func(*args, **kwargs)
    return wrapper


# HTML PAGES ---------------------------------------------------

@driver_auth.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@driver_auth.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup.html")


# API ROUTES (JSON) --------------------------------------------

@driver_auth.route("/signup", methods=["POST"])
def signup_api():

    data = request.get_json() or {}

    username = data.get("username")
    phone = data.get("phone")
    password = data.get("password")

    if not phone or not password:
        return jsonify({"error": "missing_fields"}), 400

    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "phone_exists"}), 409

    user = User(
        username=username or phone,
        phone=phone,
        created_at=datetime.utcnow()
    )
    user.set_password(password)
    user.start_trial()

    db.session.add(user)
    db.session.commit()

    return jsonify({"status": "success"}), 201


@driver_auth.route("/login", methods=["POST"])
def login_driver():

    data = request.get_json() or {}

    phone = data.get("phone")
    password = data.get("password")

    user = User.query.filter_by(phone=phone).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "success"}), 200


@driver_auth.route("/logout", methods=["POST"])
def logout_driver():
    session.pop("user_id", None)
    return jsonify({"status": "logged_out"}), 200


@driver_auth.route("/home")
@login_required
def driver_home():
    return render_template("driver.html")
