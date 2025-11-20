# receiver_routes.py
from flask import Blueprint, render_template, abort
from datetime import datetime
from models import JoinToken, Delivery

receiver_bp = Blueprint("receiver", __name__)

@receiver_bp.route("/t/<token>")
def open_tracking_page(token):

    # Token stored as primary key
    join_token = JoinToken.query.get(token)
    if not join_token:
        return abort(404)

    # Expiration check
    if join_token.expires_at and join_token.expires_at < datetime.utcnow():
        return abort(410)  # token expired

    # Fetch the delivery
    delivery = Delivery.query.get(join_token.delivery_id)
    if not delivery:
        return abort(404)

    # Render receiver map page
    return render_template(
        "track.html",
        token=token,
        delivery_id=delivery.id
    )
