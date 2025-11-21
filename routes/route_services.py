from flask import Blueprint, request, jsonify, current_app
import requests

route_bp = Blueprint("route_bp", __name__)

@route_bp.route("/api/route", methods=["POST"])
def get_route():
    data = request.get_json()
    start = data.get("start")   # [lat, lng]
    end = data.get("end")       # [lat, lng]

    if not start or not end:
        return jsonify({"error": "missing_coordinates"}), 400

    ORS_KEY = current_app.config["ORS_API_KEY"]

    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_KEY, "Content-Type": "application/json"}

    body = {
        "coordinates": [
            [start[1], start[0]],  # ORS expects lng, lat
            [end[1], end[0]]
        ]
    }

    response = requests.post(url, json=body, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "ors_failed"}), 500

    data = response.json()

    route_geometry = data["features"][0]["geometry"]["coordinates"]
    summary = data["features"][0]["properties"]["summary"]

    return jsonify({
        "route": route_geometry,
        "distance_m": summary["distance"],
        "duration_s": summary["duration"]
    })
