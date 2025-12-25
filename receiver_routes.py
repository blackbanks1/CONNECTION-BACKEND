from flask import Blueprint, render_template, abort, jsonify, request
from datetime import datetime
from models import db, JoinToken, Delivery

receiver_bp = Blueprint("receiver_bp", __name__)

@receiver_bp.route("/<token>", methods=["GET"])
def open_tracking_page(token):
    """Open the tracking page for a receiver using a join token."""

    # Look up token
    join_token = JoinToken.query.filter_by(token=token).first()
    if not join_token:
        if request.accept_mimetypes.accept_json:
            return jsonify({"error": "invalid_token"}), 404
        return abort(404)

    # Expiration check
    if join_token.expires_at and join_token.expires_at < datetime.utcnow():
        if request.accept_mimetypes.accept_json:
            return jsonify({"error": "token_expired"}), 410
        return abort(410)

    # Fetch delivery
    delivery = Delivery.query.get(join_token.delivery_id)
    if not delivery:
        if request.accept_mimetypes.accept_json:
            return jsonify({"error": "delivery_not_found"}), 404
        return abort(404)

    # Render receiver map page
    return render_template(
        "track.html",
        token=token,
        delivery_id=delivery.id,
        delivery=delivery
    )