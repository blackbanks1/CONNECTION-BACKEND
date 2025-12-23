from flask import Blueprint, request, jsonify, url_for, session
from datetime import datetime
from models import db, User, Delivery, JoinToken
from sqlalchemy.exc import IntegrityError

driver_bp = Blueprint("driver_bp", __name__)

# ---------------------------
# HELPER: Check subscription
# ---------------------------
def driver_has_active_subscription(driver):
    """Check if driver has an active subscription or trial period safely."""
    now = datetime.utcnow()
    trial_end = getattr(driver, "trial_end_date", None)

    if trial_end and now < trial_end:
        return True

    # TODO: Replace with real subscription logic when ready
    return True


# ---------------------------------------
# DRIVER CREATES A NEW DELIVERY SESSION
# ---------------------------------------
@driver_bp.route("/create-session", methods=["POST"])
def create_session():
    """Driver creates a new delivery session with tracking link."""
    data = request.get_json() or {}

    # ---- Session safety ----
    driver_id = session.get("user_id")
    if not driver_id:
        return jsonify({"error": "no_user_in_session"}), 401

    driver = User.query.get(driver_id)
    if not driver:
        return jsonify({"error": "driver_not_logged_in"}), 401

    # ---- Subscription check ----
    if not driver_has_active_subscription(driver):
        return jsonify({"error": "subscription_expired"}), 403

    try:
        # ---- Create delivery ----
        delivery = Delivery(
            user_id=driver.id,             # requester is the driver here
            driver_id=driver.id,
            delivery_type="standard",      # default type
            origin_address="N/A",          # placeholder, required field
            destination_address="N/A",     # placeholder, required field
            status="pending",
            created_at=datetime.utcnow()
        )
        db.session.add(delivery)

        # ---- Update driver stats ----
        driver.last_session_at = datetime.utcnow()
        driver.total_sessions = (driver.total_sessions or 0) + 1
        db.session.add(driver)

        # ---- Commit both updates ----
        db.session.commit()

        # ---- Create tracking token ----
        try:
            token = JoinToken.generate(delivery_id=delivery.id, hours=24)
            if not hasattr(token, "token"):
                raise ValueError("JoinToken.generate did not return a valid token")
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "token_generation_failed", "details": str(e)}), 500

        # ---- Build secure tracking link ----
        tracking_link = url_for(
            "receiver_bp.open_tracking_page",  # endpoint name matches function
            token=token.token,
            _external=True
        )
        # This will generate: http://<domain>/t/<token>

        return jsonify({
            "status": "success",
            "delivery_id": delivery.id,
            "tracking_link": tracking_link
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "integrity_error", "details": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "db_error", "details": str(e)}), 500