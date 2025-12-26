from flask import Blueprint, request, jsonify, url_for, session, current_app
from datetime import datetime, timedelta
from models import db, User, Delivery
from utils import normalizeRwandaNumber
from sqlalchemy.exc import IntegrityError
import uuid
import logging

driver_bp = Blueprint("driver_bp", __name__)
logger = logging.getLogger(__name__)

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

# ---------------------------
# HELPER: Generate tracking token
# ---------------------------
def generate_tracking_token(delivery_id):
    """Generate a simple tracking token for the delivery."""
    # Using delivery_id + timestamp hash for simplicity
    # In production, use a proper JWT or signed token
    import hashlib
    import time
    
    raw = f"{delivery_id}-{time.time()}-{uuid.uuid4()}"
    token = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return token

# ---------------------------------------
# DRIVER CREATES A NEW DELIVERY SESSION
# ---------------------------------------
@driver_bp.route("/create-session", methods=["POST"])
def create_session():
    """Driver creates a new delivery session with tracking link."""
    data = request.get_json() or {}
    
    logger.info(f"Creating session with data: {data}")

    # ---- Session safety ----
    driver_id = session.get("user_id")
    if not driver_id:
        return jsonify({"error": "no_user_in_session"}), 401

    driver = User.query.get(driver_id)
    if not driver:
        return jsonify({"error": "driver_not_logged_in"}), 401

    # ---- Validate receiver phone ----
    receiver_phone = data.get("receiver_phone", "").strip()
    if not receiver_phone:
        return jsonify({"error": "receiver_phone_required"}), 400
    
    # Normalize phone number
    normalized_phone = normalizeRwandaNumber(receiver_phone)
    if not normalized_phone:
        return jsonify({"error": "invalid_phone_format"}), 400
    
    # ---- Subscription check ----
    if not driver_has_active_subscription(driver):
        return jsonify({"error": "subscription_expired"}), 403

    try:
        # ---- Create delivery ----
        delivery = Delivery(
            driver_id=driver.id,
            receiver_phone=normalized_phone,
            receiver_name=data.get("receiver_name"),
            status="pending",
            created_at=datetime.utcnow(),
            socket_room=str(uuid.uuid4())  # Unique room for socket.io
        )
        db.session.add(delivery)
        db.session.flush()  # Get the ID without committing
        
        # ---- Update driver stats ----
        driver.last_session_at = datetime.utcnow()
        driver.total_sessions = (driver.total_sessions or 0) + 1
        db.session.add(driver)

        # ---- Commit to get delivery ID ----
        db.session.commit()
        
        logger.info(f"Delivery created: {delivery.id} for driver {driver.id}")

        # ---- Build tracking link ----
        # Using delivery_id instead of token for simplicity
        tracking_link = url_for(
            "tracking_page",  # We'll create this route
            delivery_id=delivery.delivery_id,  # Use public UUID
            _external=True
        )
        
        # Alternative: Direct track URL
        base_url = current_app.config.get('BASE_URL', request.host_url.rstrip('/'))
        tracking_link = f"{base_url}/track/{delivery.delivery_id}"

        return jsonify({
            "status": "success",
            "delivery_id": delivery.delivery_id,  # Public UUID
            "tracking_link": tracking_link,
            "socket_room": delivery.socket_room,
            "receiver_phone": normalized_phone
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Integrity error: {e}")
        return jsonify({"error": "database_error", "details": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "server_error", "details": str(e)}), 500

# ---------------------------------------
# DRIVER ENDS DELIVERY SESSION
# ---------------------------------------
@driver_bp.route("/end-session", methods=["POST"])
def end_session():
    """Driver ends an active delivery session."""
    data = request.get_json() or {}
    
    driver_id = session.get("user_id")
    if not driver_id:
        return jsonify({"error": "no_user_in_session"}), 401

    delivery_id = data.get("delivery_id")
    if not delivery_id:
        return jsonify({"error": "delivery_id_required"}), 400

    try:
        # Find delivery by public UUID
        delivery = Delivery.query.filter_by(delivery_id=delivery_id).first()
        if not delivery:
            return jsonify({"error": "delivery_not_found"}), 404
        
        # Check if driver owns this delivery
        if delivery.driver_id != driver_id:
            return jsonify({"error": "not_authorized"}), 403
        
        # Update delivery status
        delivery.status = "completed"
        delivery.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Delivery {delivery_id} ended by driver {driver_id}")
        
        return jsonify({
            "status": "success",
            "message": "Delivery session ended"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error ending session: {e}")
        return jsonify({"error": "server_error"}), 500

# ---------------------------------------
# DRIVER GETS ACTIVE DELIVERIES
# ---------------------------------------
@driver_bp.route("/active-deliveries", methods=["GET"])
def get_active_deliveries():
    """Get all active deliveries for the current driver."""
    driver_id = session.get("user_id")
    if not driver_id:
        return jsonify({"error": "no_user_in_session"}), 401
    
    active_deliveries = Delivery.query.filter_by(
        driver_id=driver_id,
        status="active"
    ).all()
    
    return jsonify({
        "status": "success",
        "deliveries": [delivery.to_dict() for delivery in active_deliveries]
    }), 200