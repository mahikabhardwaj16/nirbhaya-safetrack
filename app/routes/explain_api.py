# Nirbhaya SafeTrack - Explain API

from flask import Blueprint, request, jsonify
from ..engine.explainer import generate_explanation, compute_dominant_factors

explain_api = Blueprint("explain_api", __name__, url_prefix="/api/explain")


@explain_api.route("/route", methods=["GET"])
def explain_route():
    route_data = request.args.get("route_data")
    mode = request.args.get("mode", "balanced")
    hour = int(request.args.get("hour", 20))

    if not route_data:
        return jsonify({"error": "route_data parameter is required"}), 400

    from ..engine.time_context import get_time_multiplier
    time_period = get_time_multiplier(hour)

    explanation = generate_explanation(route_data, {}, mode, time_period["label"])
    dominant_factors = compute_dominant_factors(route_data)

    return jsonify({
        "explanation_text": explanation,
        "dominant_factors": dominant_factors,
        "time_period": time_period["label"],
        "confidence": "high" if route_data.get("safety_score", 1) < 0.4 else "medium",
    })
