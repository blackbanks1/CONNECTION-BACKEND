import eventlet
eventlet.monkey_patch()
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

# SocketIO must be created BEFORE create_app
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

# ---------------------------------------
# JOIN TOKEN COMPATIBILITY PATCH
# ---------------------------------------
_orig_generate = getattr(JoinToken, "generate", None)

if _orig_generate:
    def _generate_compat(delivery_id, expires_in_hours=None, hours=None):
        if expires_in_hours is not None:
            return _orig_generate(delivery_id, hours=expires_in_hours)
        if hours is not None:
            return _orig_generate(delivery_id, hours=hours)
        return _orig_generate(delivery_id, hours=24)

    JoinToken.generate = staticmethod(_generate_compat)


# ---------------------------------------
# UTILS
# ---------------------------------------
def haversine_meters(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371000 * c


# ---------------------------------------
# APP FACTORY
# ---------------------------------------


# Assuming your other imports (db, blueprints, socketio, Config) are already defined
# from your current app

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(driver_bp, url_prefix="/driver")
    app.register_blueprint(driver_auth, url_prefix="/driver")
    app.register_blueprint(receiver_bp, url_prefix="/t")
    app.register_blueprint(route_bp, url_prefix="/api")

    # Attach SocketIO
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="eventlet",
        ping_timeout=25,
        ping_interval=10
    )

    # -----------------------------
    # BASIC ROUTES
    # -----------------------------
    @app.route("/")
    def index():
        return "OK - server running"

    @app.route("/driver.html")
    def driver_page():
        return render_template("driver.html")

    # -----------------------------
    # ROUTE API (GraphHopper + fallback)
    # -----------------------------

    GRAPHHOPPER_KEY = os.getenv("GRAPHHOPPER_KEY") or app.config.get("GRAPHHOPPER_KEY")
    
    def haversine_meters(lat1, lon1, lat2, lon2):
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000  # Earth radius in meters
        phi1, phi2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = sin(dphi/2)**2 + cos(phi1) * cos(phi2) * sin(dlambda/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    def interpolate_points(lat1, lng1, lat2, lng2, num_points=10):
        # Creates multiple points along a straight line between start and end
        return [
            [lat1 + (lat2 - lat1) * i / (num_points - 1),
             lng1 + (lng2 - lng1) * i / (num_points - 1)]
            for i in range(num_points)
        ]
    
    @app.route("/api/route", methods=["POST"])
    def api_route():
        data = request.get_json() or {}
        start = data.get("start") or {}
        end = data.get("end") or {}
    
        # Validate coordinates
        try:
            s_lat, s_lng = float(start["lat"]), float(start["lng"])
            e_lat, e_lng = float(end["lat"]), float(end["lng"])
        except Exception:
            return jsonify({"error": "invalid_coordinates"}), 400
    
        # Default fallback: interpolated polyline + ETA
        polyline = interpolate_points(s_lat, s_lng, e_lat, e_lng, num_points=10)
        distance_m = haversine_meters(s_lat, s_lng, e_lat, e_lng)
        distance_km = distance_m / 1000.0
        avg_kmh = 30.0
        eta_min = (distance_km / avg_kmh) * 60.0
        via = "estimate"
    
        # Use GraphHopper if key available
        if GRAPHHOPPER_KEY:
            try:
                url = (
                    f"https://graphhopper.com/api/1/route?"
                    f"point={s_lat},{s_lng}&point={e_lat},{e_lng}"
                    f"&vehicle=car&locale=en&points_encoded=false"
                    f"&instructions=true&key={GRAPHHOPPER_KEY}"
                )
                r = requests.get(url, timeout=40)
                r.raise_for_status()
                j = r.json()
    
                if "paths" in j and len(j["paths"]) > 0:
                    path = j["paths"][0]
                    gh_coords = path.get("points", {}).get("coordinates", [])
    
                    # If GH returned >= 2 points, use them
                    if len(gh_coords) >= 2:
                        polyline = [[lat, lng] for lng, lat in gh_coords]
                        distance_km = path.get("distance", distance_m)/1000.0
                        gh_time_sec = path.get("time", 0)/1000.0
                        if gh_time_sec > 0:
                            eta_min = gh_time_sec / 60.0
                        via = "graphhopper"
    
                    # If GH returned too few points, interpolate more points along start→end
                    elif len(gh_coords) == 1:
                        polyline = interpolate_points(s_lat, s_lng, e_lat, e_lng, num_points=10)
                        via = "interpolated"
    
            except Exception:
                # GH failed; fallback already set
                pass
    
        return jsonify({
            "polyline": polyline,
            "distance_km": distance_km,
            "eta_min": eta_min,
            "via": via
        })

# ---------------------------------------
# APP + SOCKETIO EVENTS
# ---------------------------------------
app = create_app()

@socketio.on("join_delivery")
def on_join_delivery(data):
    with app.app_context():
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
            

            
            print("Client joined:", role, "delivery_id:", delivery_id)

        join_room(str(delivery_id))
        emit("join_delivery", {"delivery_id": delivery_id, "role": role})


@socketio.on("driver_update")
def on_driver_update(data):
    with app.app_context():
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
            "speed": data.get("speed"),
            "ts": datetime.utcnow().isoformat()
        }

        emit("driver_update", payload, room=str(delivery_id), include_self=False)



@socketio.on("receiver_update")
def on_receiver_update(data):
    with app.app_context():
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


# ---------------------------------------
# LOCAL DEV
# ---------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
