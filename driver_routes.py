from flask import Blueprint, request, jsonify, url_for, session
from datetime import datetime, timedelta
from models import db, User, Delivery, JoinToken

driver_bp = Blueprint("driver_bp", __name__)

# ---------------------------
# HELPER: Check subscription
# ---------------------------
def driver_has_active_subscription(driver: User):
    # Free trial active?
    if driver.trial_end_date and datetime.utcnow() < driver.trial_end_date:
        return True

    # Daily pass active?
    if driver.daily_pass_expires and datetime.utcnow() < driver.daily_pass_expires:
        return True

    return True






# ---------------------------------------
# DRIVER CREATES A NEW DELIVERY SESSION
# ---------------------------------------

@driver_bp.route("/create-session", methods=["POST"])
def create_session():
    data = request.get_json()

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

    # -------- Create delivery ----------
    delivery = Delivery(
        driver_id=driver.id,
        receiver_phone=receiver_phone,
        created_at=datetime.utcnow()
    )
    db.session.add(delivery)
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
    })
