from flask import Blueprint, render_template, request, jsonify, abort, current_app
from datetime import datetime
from models import db, Delivery
from utils import normalizeRwandaNumber
import logging

receiver_bp = Blueprint("receiver_bp", __name__, url_prefix="/track")
logger = logging.getLogger(__name__)

@receiver_bp.route("/<delivery_id>", methods=["GET"])
def tracking_page(delivery_id):
    """Open the tracking page for a receiver using delivery ID."""
    
    logger.info(f"Accessing tracking page for delivery: {delivery_id}")
    
    # Find delivery by public UUID
    delivery = Delivery.query.filter_by(delivery_id=delivery_id).first()
    if not delivery:
        if request.accept_mimetypes.accept_json:
            return jsonify({"error": "delivery_not_found"}), 404
        return abort(404, description="Delivery not found")
    
    # Check if delivery is still active
    if delivery.status not in ["pending", "active", "in_progress"]:
        if request.accept_mimetypes.accept_json:
            return jsonify({"error": "delivery_ended", "status": delivery.status}), 410
        return abort(410, description="This delivery has ended")
    
    # Render receiver map page
    return render_template(
        "track.html",
        delivery_id=delivery.delivery_id,
        receiver_phone=delivery.receiver_phone,
        status=delivery.status,
        created_at=delivery.created_at
    )

@receiver_bp.route("/<delivery_id>/status", methods=["GET"])
def delivery_status(delivery_id):
    """Get delivery status (API endpoint)."""
    
    delivery = Delivery.query.filter_by(delivery_id=delivery_id).first()
    if not delivery:
        return jsonify({"error": "delivery_not_found"}), 404
    
    return jsonify({
        "status": "success",
        "delivery": delivery.to_dict()
    }), 200

@receiver_bp.route("/end-delivery", methods=["POST"])
def end_delivery():
    """Receiver or driver ends a delivery session."""
    data = request.get_json() or {}
    
    delivery_id = data.get("delivery_id")
    if not delivery_id:
        return jsonify({"error": "delivery_id_required"}), 400
    
    delivery = Delivery.query.filter_by(delivery_id=delivery_id).first()
    if not delivery:
        return jsonify({"error": "delivery_not_found"}), 404
    
    # Update delivery status
    delivery.status = "completed"
    delivery.completed_at = datetime.utcnow()
    
    try:
        db.session.commit()
        logger.info(f"Delivery {delivery_id} marked as completed")
        
        return jsonify({
            "status": "success",
            "message": "Delivery completed successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error ending delivery: {e}")
        return jsonify({"error": "server_error"}), 500

@receiver_bp.route("/validate-phone", methods=["POST"])
def validate_receiver_phone():
    """Validate if a phone number matches a delivery."""
    data = request.get_json() or {}
    
    delivery_id = data.get("delivery_id", "").strip()
    phone = data.get("phone", "").strip()
    
    if not delivery_id or not phone:
        return jsonify({"error": "delivery_id_and_phone_required"}), 400
    
    # Normalize phone
    normalized_phone = normalizeRwandaNumber(phone)
    if not normalized_phone:
        return jsonify({"error": "invalid_phone_format"}), 400
    
    # Find delivery
    delivery = Delivery.query.filter_by(delivery_id=delivery_id).first()
    if not delivery:
        return jsonify({"error": "delivery_not_found"}), 404
    
    # Check if phone matches
    if delivery.receiver_phone != normalized_phone:
        return jsonify({"error": "phone_not_authorized"}), 403
    
    return jsonify({
        "status": "success",
        "message": "Phone authorized",
        "delivery": delivery.to_dict()
    }), 200