from flask import Blueprint, request, jsonify, current_app
import requests

route_bp = Blueprint("route_bp", __name__)

@route_bp.route("/api/route", methods=["POST"])
def get_route():
    """Fetch a driving route from GraphHopper given start and end coordinates."""
    data = request.get_json() or {}
    start = data.get("start")   # expected [lat, lng]
    end = data.get("end")       # expected [lat, lng]

    # Validate input
    if not (isinstance(start, list) and len(start) == 2):
        return jsonify({"error": "invalid_start_coordinates"}), 400
    if not (isinstance(end, list) and len(end) == 2):
        return jsonify({"error": "invalid_end_coordinates"}), 400

    # Get API key safely
    GH_KEY = current_app.config.get("GRAPHHOPPER_KEY")
    if not GH_KEY:
        return jsonify({"error": "missing_graphhopper_api_key"}), 500

    url = "https://graphhopper.com/api/1/route"
    params = {
        "point": [f"{start[0]},{start[1]}", f"{end[0]},{end[1]}"],
        "vehicle": "car",
        "locale": "en",
        "key": GH_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        return jsonify({"error": "graphhopper_request_failed", "details": str(e)}), 502

    if response.status_code != 200:
        return jsonify({
            "error": "graphhopper_failed",
            "status_code": response.status_code,
            "details": response.text
        }), 502

    try:
        data = response.json()
        path = data["paths"][0]
        route_geometry = path["points"]  # encoded polyline
        distance_m = path["distance"]
        duration_s = path["time"] / 1000  # GraphHopper returns ms
    except (KeyError, IndexError, ValueError) as e:
        return jsonify({"error": "graphhopper_response_invalid", "details": str(e)}), 500

    return jsonify({
        "route": route_geometry,
        "distance_m": distance_m,
        "duration_s": duration_s
    }), 200