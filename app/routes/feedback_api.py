# Nirbhaya SafeTrack - Community Feedback API

from flask import Blueprint, request, jsonify, current_app
from ..engine.community_feedback import (
    get_recent_feedback,
    get_feedback_stats,
    submit_feedback,
    get_feedback_penalty,
    FEEDBACK_TYPES,
)

feedback_api = Blueprint("feedback_api", __name__, url_prefix="/api/feedback")


@feedback_api.route("/recent", methods=["GET"])
def recent():
    limit = request.args.get("limit", 10, type=int)
    since = request.args.get("since", None)
    items = get_recent_feedback(limit=limit, since=since)
    return jsonify({"feedback": items, "total": len(items)})


@feedback_api.route("/stats", methods=["GET"])
def stats():
    data = get_feedback_stats()
    return jsonify(data)


@feedback_api.route("/report", methods=["POST"])
def report():
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body is required"}), 400

    ftype = body.get("type")
    zone_id = body.get("zone_id")
    message = body.get("message", "").strip()
    severity = body.get("severity", 1)

    if ftype not in FEEDBACK_TYPES:
        return jsonify({"error": f"Invalid type. Must be one of: {', '.join(FEEDBACK_TYPES)}"}), 400
    if not zone_id:
        return jsonify({"error": "zone_id is required"}), 400
    if not message or len(message) < 5:
        return jsonify({"error": "Message must be at least 5 characters"}), 400

    item = submit_feedback(ftype, zone_id, message, severity)
    return jsonify({"success": True, "feedback": item}), 201


@feedback_api.route("/types", methods=["GET"])
def types():
    return jsonify({"types": FEEDBACK_TYPES})


@feedback_api.route("/penalty", methods=["GET"])
def penalty():
    zone_id = request.args.get("zone_id")
    hour = request.args.get("hour", 20, type=int)
    if not zone_id:
        return jsonify({"error": "zone_id is required"}), 400
    penalty_val = get_feedback_penalty(zone_id, hour)
    return jsonify({"zone_id": zone_id, "hour": hour, "community_penalty": penalty_val})
