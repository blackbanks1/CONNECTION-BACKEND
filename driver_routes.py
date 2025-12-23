from flask import Blueprint, request, jsonify, url_for, session
from datetime import datetime
from models import db, User, Delivery, JoinToken

driver_bp = Blueprint("driver_bp", __name__)

# ---------------------------
# HELPER: Check subscription
# ---------------------------
def driver_has_active_subscription(driver):
    """Check if driver has an active subscription or trial period safely."""
    now = datetime.utcnow()

    # Safely get trial_end_date if it exists
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

    driver_id = session.get("user_id")
    driver = User.query.get(driver_id)
    if not driver:
        return jsonify({"error": "driver_not_logged_in"}), 401

    receiver_phone = data.get("receiver_phone")
    if not receiver_phone:
        return jsonify({"error": "missing_receiver_phone"}), 400

    # -------- Subscription / Free trial check --------
    if not driver_has_active_subscription(driver):
        return jsonify({"error": "subscription_expired"}), 403

    try:
        # -------- Create delivery ----------
        delivery = Delivery(
            driver_id=driver.id,
            receiver_phone=receiver_phone,
            created_at=datetime.utcnow(),
            status="pending"  # example field
        )
        db.session.add(delivery)

        # -------- Update driver stats ----------
        driver.last_session_at = datetime.utcnow()
        driver.total_sessions = (driver.total_sessions or 0) + 1
        db.session.add(driver)

        # -------- Commit both updates ----------
        db.session.commit()

        # -------- Create tracking token --------
        token = JoinToken.generate(delivery_id=delivery.id, hours=24)

        # -------- Build secure tracking link --------
        tracking_link = url_for(
            "receiver_bp.open_tracking_page",
            token=token.token,
            _external=True
        )

        return jsonify({
            "status": "success",
            "delivery_id": delivery.id,
            "tracking_link": tracking_link
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "db_error", "details": str(e)}), 500