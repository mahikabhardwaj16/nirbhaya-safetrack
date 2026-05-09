# Nirbhaya SafeTrack - Route API

import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from ..engine.dijkstra_runner import find_route, find_all_routes, run_dijkstra, build_weighted_graph
from ..engine.time_context import get_time_multiplier
from ..engine.explainer import generate_explanation, generate_route_summary
from ..engine.safety_scorer import compute_safety_score, get_factor_breakdown

route_api = Blueprint("route_api", __name__, url_prefix="/api/route")


def log_error(endpoint, error):
    current_app.logger.error("=== ROUTE API ERROR [%s] ===", endpoint)
    current_app.logger.error("Message: %s", str(error))
    current_app.logger.error("Traceback:\n%s", traceback.format_exc())


def parse_hour(departure_time):
    try:
        if departure_time is not None:
            ts = str(departure_time)
            if ":" in ts:
                hour = int(ts.split(":")[0])
            else:
                hour = int(ts)
            return max(0, min(23, hour))
    except (ValueError, AttributeError):
        pass
    return datetime.now().hour


@route_api.route("/compute", methods=["POST"])
def compute_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        origin = data.get("origin")
        destination = data.get("destination")
        departure_time = data.get("departure_time")
        hour = parse_hour(departure_time)
        mode = data.get("mode", "balanced")
        user_preferences = data.get("user_preferences")
        if not user_preferences:
            user_preferences = data.get("preferences")
        waypoints = data.get("waypoints", [])

        if not origin or not destination:
            return jsonify({"error": "origin and destination are required"}), 400

        graph = current_app.config.get("graph")
        datasets = current_app.config.get("datasets")

        if not graph or not datasets:
            return jsonify({"error": "Graph not initialized"}), 500

        if mode not in ["fastest", "safest", "balanced", "all"]:
            return jsonify({"error": "mode must be one of: fastest, safest, balanced, all"}), 400

        compute_modes = ["fastest", "safest", "balanced"] if mode == "all" else [mode]

        all_results = {}
        for m in compute_modes:
            partial = find_all_routes(graph, datasets, origin, destination, hour, user_preferences, waypoints)
            all_results.update(partial)

        if not all_results:
            return jsonify({"error": "No route found between these nodes"}), 404

        response = {}
        for route_mode, route_data in all_results.items():
            time_period = get_time_multiplier(hour)
            explanation = generate_explanation(route_data, all_results, route_mode, time_period["label"])
            node_names = {n: d.get("name", n) for n, d in graph.nodes(data=True)}
            summary = generate_route_summary(route_data, route_mode, node_names)

            segment_risks = []
            factor_breakdowns = []
            path = route_data["path"]
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge = graph[u][v]
                zone_id = graph.nodes[u].get("zone_id", "")
                za = datasets["zone_attributes"].get(zone_id, {
                    "lighting_score": 0.5, "crowd_density_night": 0.5,
                    "isolation_index": 0.5, "emergency_facility_within_500m": False,
                    "transit_accessibility": 0.5,
                })
                edge_data = {"zone_id": zone_id, "distance_m": edge.get("distance_m", 100)}
                seg_score = compute_safety_score(edge_data, za, datasets["crime_incidents"], hour)

                is_night = hour >= 20 or hour < 6
                is_low_vis = seg_score > 0.4 and is_night and za.get("lighting_score", 0.5) < 0.4

                u_data = graph.nodes[u]
                v_data = graph.nodes[v]
                segment_risks.append({
                    "node_id": u,
                    "name": node_names.get(u, u),
                    "zone_id": zone_id,
                    "risk_score": round(seg_score, 3),
                    "distance_m": edge.get("distance_m", 100),
                    "is_low_visibility": is_low_vis,
                    "lighting_score": za.get("lighting_score", 0.5),
                    "isolation_index": za.get("isolation_index", 0.5),
                    "lat_start": u_data.get("lat"),
                    "lon_start": u_data.get("lon"),
                    "lat_end": v_data.get("lat"),
                    "lon_end": v_data.get("lon"),
                })

                breakdown = get_factor_breakdown(edge_data, za, datasets["crime_incidents"], hour, user_preferences)
                factor_breakdowns.append(breakdown)

            high_risk_segments = [s for s in segment_risks if s["risk_score"] > 0.5]

            response[route_mode] = {
                "path": route_data["path"],
                "coordinates": route_data.get("coordinates"),
                "distance_m": route_data["distance_m"],
                "safety_score": route_data["safety_score"],
                "explanation": explanation,
                "summary": summary,
                "segment_risks": segment_risks,
                "factor_breakdowns": factor_breakdowns,
                "high_risk_segments": high_risk_segments,
                "nearby_emergency": _find_nearby_emergency(graph, datasets, route_data["path"]),
            }

        response["_comparison"] = _build_comparison_data(all_results)
        response["_safety_intelligence"] = _build_safety_intelligence(datasets, hour)

        return jsonify(response)

    except Exception as e:
        log_error("compute_route", e)
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


def _find_nearby_emergency(graph, datasets, path):
    facilities = datasets.get("emergency_facilities", [])
    nearby = []

    for node_id in path:
        node_data = graph.nodes[node_id]
        node_lat = node_data.get("lat", 0)
        node_lon = node_data.get("lon", 0)

        for fac in facilities:
            dist = _haversine(node_lat, node_lon, fac["lat"], fac["lon"])
            if dist < 300:
                nearby.append({
                    "facility_id": fac["facility_id"],
                    "type": fac["type"],
                    "name": fac["name"],
                    "distance_m": round(dist),
                    "operational_24h": fac["operational_24h"],
                    "lat": fac["lat"],
                    "lon": fac["lon"],
                    "near_node": node_id,
                })

    seen = set()
    unique = []
    for item in nearby:
        key = item["facility_id"]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return sorted(unique, key=lambda x: x["distance_m"])[:10]


def _build_comparison_data(all_results):
    comparison = {}
    modes = list(all_results.keys())

    for mode in modes:
        route = all_results[mode]
        others = {m: all_results[m] for m in modes if m != mode}

        tradeoffs = []
        for other_mode, other_route in others.items():
            time_diff = round((route["distance_m"] - other_route["distance_m"]) / 80)
            safety_diff = round((route["safety_score"] - other_route["safety_score"]) * 100)

            tradeoffs.append({
                "compared_to": other_mode,
                "time_diff_min": time_diff,
                "safety_diff_pct": safety_diff,
                "is_faster": time_diff < 0,
                "is_safer": safety_diff < 0,
            })

        comparison[mode] = {
            "distance_m": route["distance_m"],
            "safety_score": route["safety_score"],
            "tradeoffs": tradeoffs,
        }

    return comparison


def _build_safety_intelligence(datasets, hour):
    crime_data = datasets.get("crime_incidents", [])
    zones = datasets.get("zone_attributes", {})
    facilities = datasets.get("emergency_facilities", [])

    total_incidents = len(crime_data)
    total_zones = len(zones)

    time_periods = ['Late Night', 'Late Night', 'Late Night', 'Late Night', 'Late Night',
                    'Dawn', 'Dawn', 'Morning', 'Morning', 'Daytime', 'Daytime', 'Daytime',
                    'Daytime', 'Daytime', 'Daytime', 'Daytime', 'Evening', 'Evening',
                    'Evening', 'Night', 'Night', 'Night', 'Night', 'Night']

    high_risk_zones = 0
    for zid, za in zones.items():
        edge_data = {"zone_id": zid}
        from ..engine.safety_scorer import compute_safety_score
        score = compute_safety_score(edge_data, za, crime_data, hour)
        if score > 0.5:
            high_risk_zones += 1

    from ..engine.community_feedback import get_feedback_stats
    fb_stats = get_feedback_stats()

    return {
        "total_incidents": total_incidents,
        "total_zones": total_zones,
        "high_risk_zones": high_risk_zones,
        "total_facilities": len(facilities),
        "time_period": time_periods[hour],
        "hour": hour,
        "community_reports": fb_stats.get("total_reports", 0),
        "community_top_concerns": list(fb_stats.get("by_type", {}).keys())[:3],
    }


def _haversine(lat1, lon1, lat2, lon2):
    import math
    R = 6371000
    to_rad = lambda x: x * math.pi / 180
    dlat = to_rad(lat2 - lat1)
    dlon = to_rad(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@route_api.route("/compare", methods=["POST"])
def compare_routes():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    origin = data.get("origin")
    destination = data.get("destination")
    departure_time = data.get("departure_time")
    hour = parse_hour(departure_time)
    user_preferences = data.get("user_preferences")
    if not user_preferences:
        user_preferences = data.get("preferences")

    if not origin or not destination:
        return jsonify({"error": "origin and destination are required"}), 400

    graph = current_app.config.get("graph")
    datasets = current_app.config.get("datasets")

    if not graph or not datasets:
        return jsonify({"error": "Graph not initialized"}), 500

    all_results = find_all_routes(graph, datasets, origin, destination, hour, user_preferences)

    if not all_results:
        return jsonify({"error": "No routes found"}), 404

    comparison = {}
    for m, route_data in all_results.items():
        comparison[m] = {
            "distance_m": route_data["distance_m"],
            "safety_score": route_data["safety_score"],
            "path_length": len(route_data["path"]),
        }

    return jsonify(comparison)
