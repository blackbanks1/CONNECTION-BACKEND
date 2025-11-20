from flask import Blueprint, request, jsonify, url_for
from datetime import datetime, timedelta
from models import db, Driver, Delivery, TrackingToken

driver_bp = Blueprint("driver_bp", __name__)

# ---------------------------
# HELPER: Check subscription
# ---------------------------
def driver_has_active_subscription(driver: Driver):
    """Return True if driver can use the service."""
    
    # 1. Free trial still active
    if driver.free_trial_started:
        days_used = (datetime.utcnow() - driver.free_trial_started).days
        if days_used < 7:
            return True

    # 2. Paid daily pass still active
    if driver.subscription_until and driver.subscription_until > datetime.utcnow():
        return True

    # 3. No access
    return False


# ---------------------------------------
# DRIVER CREATES A NEW DELIVERY SESSION
# ---------------------------------------
@driver_bp.route("/create-session", methods=["POST"])
def create_session():
    data = request.get_json()
    driver_phone = request.headers.get("X-Driver-Phone")  # You may change based on your login system
    receiver_phone = data.get("receiver_phone")

    driver = Driver.query.filter_by(phone=driver_phone).first()
    if not driver:
        return jsonify({"error": "driver_not_found"}), 404

    # -------- Subscription / Free trial check --------
    if not driver_has_active_subscription(driver):
        return jsonify({"error": "subscription_expired"}), 403

    # -------- Create delivery ----------
    delivery = Delivery(
        driver_id=driver.id,
        receiver_phone=receiver_phone,
        created_at=datetime.utcnow()
    )
    db.session.add(delivery)
    db.session.commit()

    # -------- Create tracking token --------
    token = TrackingToken(
        delivery_id=delivery.id,
        token=TrackingToken.generate_token(),
        created_at=datetime.utcnow()
    )
    db.session.add(token)
    db.session.commit()

    # -------- Build secure tracking link --------
    tracking_link = url_for(
        "receiver_bp.open_tracking_page",
        token=token.token,
        _external=True,
        _scheme="https"
    )

    return jsonify({
        "status": "success",
        "delivery_id": delivery.id,
        "tracking_link": tracking_link
    })
