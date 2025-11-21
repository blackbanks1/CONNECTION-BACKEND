# app.py (final - cleaned)
import os
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

from flask import Flask, render_template, abort, request, session, jsonify
from flask_socketio import SocketIO, join_room, emit
import requests

from config import Config
from models import db, User, Delivery, JoinToken
from routes.route_services import route_bp
from driver_routes import driver_bp
from driver_auth import driver_auth
from receiver_routes import receiver_bp




# create SocketIO instance (will be initialized with app inside create_app)
socketio = SocketIO(cors_allowed_origins="*", manage_session=False)




# Compatibility wrapper: JoinToken.generate may accept different param names
_orig_generate = getattr(JoinToken, "generate", None)

if _orig_generate:
    def _generate_compat(delivery_id, expires_in_hours=None, hours=None):
        # prefer explicit param
        if expires_in_hours is not None:
            return _orig_generate(delivery_id, hours=expires_in_hours)
        if hours is not None:
            return _orig_generate(delivery_id, hours=hours)
        return _orig_generate(delivery_id, hours=24)

    # replace staticmethod with a new staticmethod
    JoinToken.generate = staticmethod(_generate_compat)



def haversine_meters(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371000 * c


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # initialize DB
    db.init_app(app)

    # register blueprints early
    app.register_blueprint(driver_bp, url_prefix="/driver")
    app.register_blueprint(driver_auth, url_prefix="/driver")
    app.register_blueprint(receiver_bp, url_prefix="/t")
    app.register_blueprint(route_bp, url_prefix="/api")
    # initialize socketio with the app
    socketio.init_app(app)

    @app.route("/")
    def index():
        return "OK - server running"

    @app.route("/driver.html")
    def driver_page():
        # serve driver dashboard template (full real-time UI)
        return render_template("driver.html")


    @app.route("/api/route", methods=["POST"])
    def api_route():
        data = request.get_json() or {}
        start = data.get("start") or {}
        end = data.get("end") or {}
        try:
            s_lat = float(start["lat"]); s_lng = float(start["lng"])
            e_lat = float(end["lat"]); e_lng = float(end["lng"])
        except Exception:
            return jsonify({"error": "invalid_coordinates"}), 400

        ORS_API_KEY = os.getenv("ORS_API_KEY") or app.config.get("ORS_API_KEY")
        if ORS_API_KEY:
            try:
                url = "https://api.openrouteservice.org/v2/directions/driving-car"
                coords = [[s_lng, s_lat], [e_lng, e_lat]]
                payload = {"coordinates": coords}
                headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
                r = requests.post(url, json=payload, headers=headers, timeout=8)
                r.raise_for_status()
                j = r.json()
                summary = j["features"][0]["properties"]["summary"]
                distance_km = summary["distance"] / 1000.0
                eta_min = summary["duration"] / 60.0
                return jsonify({"distance_km": distance_km, "eta_min": eta_min, "via": "ors"})
            except Exception:
                # fall back to estimate if ORS fails
                pass

        meters = haversine_meters(s_lat, s_lng, e_lat, e_lng)
        km = meters / 1000.0
        avg_kmh = 30.0
        eta_min = (km / avg_kmh) * 60.0
        return jsonify({"distance_km": km, "eta_min": eta_min, "via": "estimate", "assumed_kmh": avg_kmh})

    return app


# -----------------------
# SOCKET HANDLERS (use session inside handlers; socketio must be init'd with app)
# -----------------------
@socketio.on("join_delivery")
def on_join_delivery(data):
    delivery_id = data.get("delivery_id")
    role = data.get("role", "receiver")
    if not delivery_id or role not in ("driver", "receiver"):
        emit("error", {"error": "delivery_id and role required"})
        return

    if role == "driver":
        uid = session.get("user_id")
        if not uid:
            emit("error", {"error": "driver_not_logged_in"})
            return
        driver = User.query.get(uid)
        if not driver or driver.role != "driver":
            emit("error", {"error": "invalid_driver"})
            return
        delivery = Delivery.query.get(delivery_id)
        if not delivery or delivery.driver_id != driver.id:
            emit("error", {"error": "not_your_delivery"})
            return

    join_room(str(delivery_id))
    emit("join_delivery", {"delivery_id": delivery_id, "role": role}, room=str(delivery_id))


@socketio.on("driver_update")
def on_driver_update(data):
    delivery_id = data.get("delivery_id")
    if not delivery_id:
        emit("error", {"error": "delivery_id required"})
        return

    uid = session.get("user_id")
    if not uid:
        emit("error", {"error": "driver_not_logged_in"})
        return
    driver = User.query.get(uid)
    if not driver or driver.role != "driver":
        emit("error", {"error": "invalid_driver"})
        return

    delivery = Delivery.query.get(delivery_id)
    if not delivery or delivery.driver_id != driver.id:
        emit("error", {"error": "not_your_delivery"})
        return

    payload = {
        "delivery_id": delivery_id,
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "speed": data.get("speed", None),
        "ts": datetime.utcnow().isoformat()
    }
    emit("driver_update", payload, room=str(delivery_id))


@socketio.on("receiver_update")
def on_receiver_update(data):
    delivery_id = data.get("delivery_id")
    if not delivery_id:
        emit("error", {"error": "delivery_id required"})
        return

    payload = {
        "delivery_id": delivery_id,
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "ts": datetime.utcnow().isoformat()
    }
    emit("receiver_update", payload, room=str(delivery_id))


# -----------------------
# APP BOOTSTRAP
# -----------------------
app = create_app()

if __name__ == "__main__":
    # convenience: create DB tables if not present (dev only)
    with app.app_context():
        db.create_all()
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
