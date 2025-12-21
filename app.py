import eventlet
eventlet.monkey_patch()
import os
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from functools import wraps
import logging

from flask import Flask, render_template, abort, request, session, jsonify
from flask_socketio import SocketIO, join_room, emit, disconnect
import requests

from dotenv import load_dotenv
from config import Config
from models import db, User, Delivery, JoinToken
from routes.route_services import route_bp
from driver_routes import driver_bp
from driver_auth import driver_auth
from receiver_routes import receiver_bp
from admin_auth import admin_auth_bp
from admin_routes import admin_bp
from flask_jwt_extended import JWTManager

# ---------------------------------------
# LOGGING
# ---------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SocketIO must be created BEFORE create_app
socketio = SocketIO(
    cors_allowed_origins=[],  # Will be configured in create_app
    async_mode="eventlet",
    ping_timeout=25,
    ping_interval=10,
    logger=True,
    engineio_logger=True
)

# ---------------------------------------
# CONSTANTS & CONFIG
# ---------------------------------------
MIN_LAT, MAX_LAT = -90.0, 90.0
MIN_LNG, MAX_LNG = -180.0, 180.0
GRAPHHOPPER_TIMEOUT = 10  # Reduced from 40 seconds
DEFAULT_SPEED_KMH = 30.0
INTERPOLATION_POINTS = 10

# ---------------------------------------
# UTILS & HELPERS
# ---------------------------------------
def haversine_meters(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in meters using Haversine formula."""
    try:
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return 6371000 * c
    except (ValueError, TypeError) as e:
        logger.error(f"Haversine calculation error: {e}")
        return None

def validate_coordinates(lat, lng):
    """Validate latitude and longitude ranges."""
    try:
        lat = float(lat)
        lng = float(lng)
        if not (MIN_LAT <= lat <= MAX_LAT and MIN_LNG <= lng <= MAX_LNG):
            logger.info(f"Invalid lat/lng range: {lat}, {lng}")
            return None, None
        return lat, lng
    except (ValueError, TypeError):
        logger.info(f"Non-numeric lat/lng: {lat}, {lng}")
        return None, None

def interpolate_points(lat1, lng1, lat2, lng2, num_points=INTERPOLATION_POINTS):
    """Create multiple points along a straight line between start and end."""
    n = max(2, int(num_points))
    return [
        [lat1 + (lat2 - lat1) * i / (n - 1),
         lng1 + (lng2 - lng1) * i / (n - 1)]
        for i in range(n)
    ]

def authenticated_only_socketio(f):
    """Decorator to ensure user is authenticated for SocketIO events."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        uid = session.get("user_id")
        if not uid:
            emit("error", {"code": "unauthenticated", "error": "Not authenticated"})
            disconnect()
            return
        user = User.query.get(uid)
        if not user:
            emit("error", {"code": "invalid_user", "error": "Invalid user"})
            disconnect()
            return
        return f(*args, **kwargs)
    return wrapped

# ---------------------------------------
# APP FACTORY
# ---------------------------------------
def create_app():
    load_dotenv()  # Load environment variables from .env file
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # JWT configuration
    app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY")
    if not app.config['JWT_SECRET_KEY']:
        raise RuntimeError("JWT_SECRET_KEY is not set")

    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False   # True in production (HTTPS)
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # True in production with CSRF handling

    jwt = JWTManager(app)

    # Secure session configuration
    app.config['SESSION_COOKIE_SECURE'] = False  # True in production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

    app.secret_key = os.environ.get('SECRET_KEY')
    if not app.secret_key:
        raise RuntimeError("SECRET_KEY is not set")

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(driver_bp, url_prefix="/driver")
    app.register_blueprint(driver_auth, url_prefix="/driver")
    app.register_blueprint(receiver_bp, url_prefix="/t")
    app.register_blueprint(route_bp, url_prefix="/api")
    app.register_blueprint(admin_auth_bp, url_prefix="/admin/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Configure CORS for SocketIO
    allowed_origins = os.getenv("SOCKETIO_CORS_ORIGINS", "").split(",") if os.getenv("SOCKETIO_CORS_ORIGINS") else []
    if not allowed_origins or allowed_origins == ['']:
        allowed_origins = ["http://localhost:3000"]

    debug_mode = app.config.get("DEBUG", False)
    socketio.init_app(
        app,
        cors_allowed_origins=allowed_origins,
        async_mode="eventlet",
        ping_timeout=25,
        ping_interval=10,
        logger=debug_mode,
        engineio_logger=debug_mode
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

    @app.route("/api/route", methods=["POST"])
    def api_route():
        """Calculate route between two coordinates using GraphHopper with fallback."""
        data = request.get_json() or {}
        start = data.get("start") or {}
        end = data.get("end") or {}

        # Validate coordinates
        s_lat, s_lng = validate_coordinates(start.get("lat"), start.get("lng"))
        e_lat, e_lng = validate_coordinates(end.get("lat"), end.get("lng"))

        if s_lat is None or e_lat is None:
            return jsonify({"error": "invalid_coordinates"}), 400

        # Same location check
        if s_lat == e_lat and s_lng == e_lng:
            return jsonify({
                "polyline": [[s_lat, s_lng]],
                "distance_km": 0,
                "eta_min": 0,
                "via": "same_location"
            })

        # Default fallback
        polyline = interpolate_points(s_lat, s_lng, e_lat, e_lng, num_points=INTERPOLATION_POINTS)
        distance_m = haversine_meters(s_lat, s_lng, e_lat, e_lng)
        if distance_m is None:
            return jsonify({"error": "calculation_error"}), 500

        distance_km = distance_m / 1000.0
        eta_min = (distance_km / DEFAULT_SPEED_KMH) * 60.0
        via = "estimate"

        # GraphHopper if available
        if GRAPHHOPPER_KEY:
            try:
                url = (
                    f"https://graphhopper.com/api/1/route?"
                    f"point={s_lat},{s_lng}&point={e_lat},{e_lng}"
                    f"&vehicle=car&locale=en&points_encoded=false"
                    f"&instructions=true&key={GRAPHHOPPER_KEY}"
                )
                r = requests.get(url, timeout=GRAPHHOPPER_TIMEOUT)
                r.raise_for_status()
                j = r.json()

                if "paths" in j and len(j["paths"]) > 0:
                    path = j["paths"][0]
                    gh_coords = path.get("points", {}).get("coordinates", [])

                    if len(gh_coords) >= 2:
                        polyline = [[lat, lng] for lng, lat in gh_coords]
                        distance_km = (path.get("distance") or distance_m) / 1000.0
                        gh_time_sec = (path.get("time") or 0) / 1000.0
                        if gh_time_sec > 0:
                            eta_min = gh_time_sec / 60.0

                        via = "graphhopper"

                    elif len(gh_coords) == 1:
                        # If GH returned only one point, interpolate fallback
                        polyline = interpolate_points(
                            s_lat, s_lng, e_lat, e_lng,
                            num_points=INTERPOLATION_POINTS
                        )
                        via = "interpolated"

            except requests.exceptions.Timeout:
                logger.warning("GraphHopper request timed out")
            except requests.exceptions.RequestException as e:
                logger.warning(f"GraphHopper request failed: {e}")
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"GraphHopper response parsing error: {e}")

        return jsonify({
            "polyline": polyline,
            "distance_km": distance_km,
            "eta_min": eta_min,
            "via": via
        })

    return app


# ---------------------------------------
# APP + SOCKETIO EVENTS
# ---------------------------------------
app = create_app()

@socketio.on("connect")
def on_connect(auth=None):
    """Handle initial WebSocket connection with authentication."""
    uid = session.get("user_id")
    if not uid:
        logger.warning(f"Connection attempt without authentication from {request.remote_addr}")
        emit("error", {"error": "Not authenticated"})
        return False  # Reject connection
    
    user = User.query.get(uid)
    if not user:
        logger.warning(f"Connection attempt with invalid user_id {uid} from {request.remote_addr}")
        emit("error", {"error": "Invalid user"})
        return False
    
    logger.info(f"User {uid} ({user.role}) connected")
    return True

@socketio.on("disconnect")
def on_disconnect():
    """Handle WebSocket disconnection."""
    uid = session.get("user_id")
    if uid:
        logger.info(f"User {uid} disconnected")

@socketio.on("join_delivery")
@authenticated_only_socketio
def on_join_delivery(data):
    """Handle delivery room join with proper authorization."""
    delivery_id = data.get("delivery_id")
    role = data.get("role", "receiver")

    if not delivery_id or role not in ("driver", "receiver"):
        emit("error", {"error": "Invalid delivery_id or role"})
        return

    uid = session.get("user_id")
    user = User.query.get(uid)

    if role == "driver":
        if user.role != "driver":
            emit("error", {"error": "Not a driver"})
            return

        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            emit("error", {"error": "Delivery not found"})
            return
        
        if delivery.driver_id != user.id:
            logger.warning(f"Driver {uid} attempted to join delivery {delivery_id} they don't own")
            emit("error", {"error": "Not your delivery"})
            return

    elif role == "receiver":
        delivery = Delivery.query.get(delivery_id)
        if not delivery:
            emit("error", {"error": "Delivery not found"})
            return
        # Optional strict validation:
        # if delivery.receiver_id != user.id:
        #     emit("error", {"error": "Not your delivery"})
        #     return

    join_room(str(delivery_id))
    logger.info(f"User {uid} ({role}) joined delivery {delivery_id}")
    emit("join_delivery", {"delivery_id": delivery_id, "role": role})

@socketio.on("driver_update")
@authenticated_only_socketio
def on_driver_update(data):
    """Handle driver location updates with validation."""
    delivery_id = data.get("delivery_id")
    if not delivery_id:
        emit("error", {"error": "delivery_id required"})
        return

    uid = session.get("user_id")
    user = User.query.get(uid)

    if user.role != "driver":
        logger.warning(f"Non-driver user {uid} attempted driver_update")
        emit("error", {"error": "Not a driver"})
        return

    delivery = Delivery.query.get(delivery_id)
    if not delivery or delivery.driver_id != user.id:
        logger.warning(f"Driver {uid} attempted to update unauthorized delivery {delivery_id}")
        emit("error", {"error": "not_your_delivery"})
        return

    lat, lng = validate_coordinates(data.get("lat"), data.get("lng"))
    if lat is None:
        emit("error", {"error": "Invalid coordinates"})
        return

    try:
        speed = float(data.get("speed", 0))
        if speed < 0 or speed > 350:
            logger.warning(f"Invalid speed from driver {uid}, defaulting to 0")
            speed = 0
    except (ValueError, TypeError):
        speed = 0

    payload = {
        "delivery_id": delivery_id,
        "lat": lat,
        "lng": lng,
        "speed": speed,
        "ts": datetime.utcnow().isoformat()
    }

    emit("driver_update", payload, room=str(delivery_id), include_self=False)

@socketio.on("receiver_update")
@authenticated_only_socketio
def on_receiver_update(data):
    """Handle receiver location updates with validation."""
    delivery_id = data.get("delivery_id")
    if not delivery_id:
        emit("error", {"error": "delivery_id required"})
        return

    delivery = Delivery.query.get(delivery_id)
    if not delivery:
        emit("error", {"error": "Delivery not found"})
        return

    lat, lng = validate_coordinates(data.get("lat"), data.get("lng"))
    if lat is None:
        emit("error", {"error": "Invalid coordinates"})
        return

    payload = {
        "delivery_id": delivery_id,
        "lat": lat,
        "lng": lng,
        "ts": datetime.utcnow().isoformat()
    }

    emit("receiver_update", payload, room=str(delivery_id))

# ---------------------------------------
# LOCAL DEV
# ---------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        debug=os.getenv("FLASK_ENV", "development") == "development"
    )