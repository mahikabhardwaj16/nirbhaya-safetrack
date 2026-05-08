# Nirbhaya SafeTrack - Safety API

from flask import Blueprint, request, jsonify, current_app
from ..engine.safety_scorer import compute_safety_score, get_factor_breakdown, compute_crime_penalty
from ..engine.time_context import get_time_multiplier
from ..engine.community_feedback import get_feedback_penalty, get_feedback_stats

safety_api = Blueprint("safety_api", __name__, url_prefix="/api/safety")


@safety_api.route("/score", methods=["GET"])
def get_safety_score():
    zone_id = request.args.get("zone_id")
    hour = int(request.args.get("hour", 20))
    user_weights = request.args.get("weights", None)

    if not zone_id:
        return jsonify({"error": "zone_id is required"}), 400

    datasets = current_app.config.get("datasets")
    if not datasets:
        return jsonify({"error": "Datasets not initialized"}), 500

    zone_attrs = datasets["zone_attributes"].get(zone_id)
    if not zone_attrs:
        return jsonify({"error": f"Zone {zone_id} not found"}), 404

    crime_data = datasets["crime_incidents"]
    time_mult = get_time_multiplier(hour)

    edge_data = {"zone_id": zone_id}
    score = compute_safety_score(edge_data, zone_attrs, crime_data, hour, user_weights)
    breakdown = get_factor_breakdown(edge_data, zone_attrs, crime_data, hour, user_weights)

    return jsonify({
        "zone_id": zone_id,
        "hour": hour,
        "time_period": time_mult["label"],
        "score": round(score, 3),
        "factors": {k: round(v, 3) for k, v in breakdown.items()},
    })


@safety_api.route("/heatmap", methods=["GET"])
def get_heatmap():
    hour = int(request.args.get("hour", 20))
    bounds = request.args.get("bounds", None)

    datasets = current_app.config.get("datasets")
    if not datasets:
        return jsonify({"error": "Datasets not initialized"}), 500

    zone_attrs_map = datasets["zone_attributes"]
    crime_data = datasets["crime_incidents"]
    nodes = datasets["road_segments"]["nodes"]

    zone_scores = {}
    for node in nodes:
        zone_id = node["zone_id"]
        if zone_id in zone_scores:
            continue

        za = zone_attrs_map.get(zone_id, {
            "lighting_score": 0.5,
            "crowd_density_night": 0.5,
            "isolation_index": 0.5,
            "emergency_facility_within_500m": False,
            "transit_accessibility": 0.5,
        })

        edge_data = {"zone_id": zone_id}
        score = compute_safety_score(edge_data, za, crime_data, hour)

        community_penalty = get_feedback_penalty(zone_id, hour)
        feedback_stats = get_feedback_stats()
        zone_concerns = feedback_stats.get("zone_concern_count", {})
        zone_name = node.get("name", zone_id)

        zone_scores[zone_id] = {
            "zone_id": zone_id,
            "score": round(score, 3),
            "lat": node["lat"],
            "lon": node["lon"],
            "name": zone_name,
            "community_penalty": round(community_penalty, 4),
            "community_reports": feedback_stats.get("total_reports", 0),
            "zone_reports": zone_concerns.get(zone_name, 0),
            "attributes": {
                "lighting_score": round(za.get("lighting_score", 0.5), 2),
                "isolation_index": round(za.get("isolation_index", 0.5), 2),
                "emergency_facility_within_500m": za.get("emergency_facility_within_500m", False),
                "transit_accessibility": round(za.get("transit_accessibility", 0.5), 2),
                "crowd_density_night": round(za.get("crowd_density_night", 0.5), 2),
            }
        }

    return jsonify({
        "zones": list(zone_scores.values()),
        "hour": hour,
        "zone_attributes": {
            zid: {
                "lighting_score": za.get("lighting_score", 0.5),
                "isolation_index": za.get("isolation_index", 0.5),
                "emergency_facility_within_500m": za.get("emergency_facility_within_500m", False),
                "transit_accessibility": za.get("transit_accessibility", 0.5),
            }
            for zid, za in zone_attrs_map.items()
        }
    })


@safety_api.route("/emergency", methods=["GET"])
def get_emergency_facilities():
    datasets = current_app.config.get("datasets")
    if not datasets:
        return jsonify({"error": "Datasets not initialized"}), 500

    facilities = datasets.get("emergency_facilities", [])
    return jsonify({"facilities": facilities})


@safety_api.route("/segments", methods=["GET"])
def get_segment_risk():
    hour = int(request.args.get("hour", 20))

    datasets = current_app.config.get("datasets")
    if not datasets:
        return jsonify({"error": "Datasets not initialized"}), 500

    graph = current_app.config.get("graph")
    if not graph:
        return jsonify({"error": "Graph not initialized"}), 500

    zone_attrs_map = datasets["zone_attributes"]
    crime_data = datasets["crime_incidents"]
    nodes = datasets["road_segments"]["nodes"]

    segments = []
    for u, v, d in graph.edges(data=True):
        zone_id = graph.nodes[u].get("zone_id", "")
        za = zone_attrs_map.get(zone_id, {
            "lighting_score": 0.5,
            "crowd_density_night": 0.5,
            "isolation_index": 0.5,
            "emergency_facility_within_500m": False,
            "transit_accessibility": 0.5,
        })

        from ..engine.safety_scorer import compute_safety_score
        edge_data = {"zone_id": zone_id, "distance_m": d.get("distance_m", 100)}
        score = compute_safety_score(edge_data, za, crime_data, hour)

        is_night = hour >= 20 or hour < 6
        lighting_risk = score > 0.4 and is_night and za.get("lighting_score", 0.5) < 0.4

        segments.append({
            "source": u,
            "target": v,
            "lat_start": graph.nodes[u].get("lat"),
            "lon_start": graph.nodes[u].get("lon"),
            "lat_end": graph.nodes[v].get("lat"),
            "lon_end": graph.nodes[v].get("lon"),
            "zone_id": zone_id,
            "risk_score": round(score, 3),
            "distance_m": d.get("distance_m", 100),
            "is_low_visibility": lighting_risk,
            "lighting_score": za.get("lighting_score", 0.5),
            "isolation_index": za.get("isolation_index", 0.5),
        })

    return jsonify({"segments": segments, "hour": hour})
