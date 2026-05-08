# Nirbhaya SafeTrack - Safety Scorer Engine

import math
from datetime import datetime, timedelta
from .time_context import get_time_multiplier

CRIME_SEVERITY_MAP = {
    "harassment": 3,
    "theft": 4,
    "assault": 7,
    "robbery": 8,
    "kidnapping": 10,
}

DEFAULT_WEIGHTS = {
    "crime": 0.30,
    "lighting": 0.20,
    "isolation": 0.20,
    "crowd": 0.10,
    "emergency": 0.10,
    "transit": 0.10,
}

COMMUNITY_FACTOR_WEIGHT = 0.15


def compute_crime_penalty(zone_id, crime_data, time_mult, reference_date=None):
    if reference_date is None:
        reference_date = datetime.now()

    if isinstance(crime_data, dict):
        zone_incidents = crime_data.get(zone_id, [])
    else:
        zone_incidents = [inc for inc in crime_data if inc.get("zone_id") == zone_id]

    if not zone_incidents:
        return 0.1

    weighted_severity = 0.0

    for incident in zone_incidents:
        severity = CRIME_SEVERITY_MAP.get(incident.get("type", ""), 3)

        ts = incident.get("timestamp")
        if isinstance(ts, datetime):
            incident_date = ts
        else:
            try:
                incident_date = datetime.strptime(str(ts), "%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                continue

        hours_ago = max((reference_date - incident_date).total_seconds() / 3600, 1)
        recency_weight = math.exp(-0.005 * hours_ago)

        incident_hour = incident_date.hour
        incident_time_mult = get_time_multiplier(incident_hour)
        time_alignment = (
            1.0 if incident_time_mult["label"] == time_mult["label"]
            else 0.5
        )

        weighted_severity += severity * recency_weight * time_alignment

    normalized = min(weighted_severity / 100.0, 1.0)
    return normalized * time_mult.get("crime", 1.0)


def get_community_penalty_for_zone(zone_id, hour):
    try:
        from .community_feedback import get_feedback_penalty
        return get_feedback_penalty(zone_id, hour)
    except Exception:
        return 0.0


def compute_safety_score(edge_data, zone_attrs, crime_data, hour, user_weights=None, reference_date=None):
    weights = dict(user_weights) if user_weights else dict(DEFAULT_WEIGHTS)

    total_w = sum(weights.values())
    if total_w == 0:
        weights = dict(DEFAULT_WEIGHTS)
        total_w = 1.0
    weights = {k: v / total_w for k, v in weights.items()}

    time_mult = get_time_multiplier(hour)
    zone_id = edge_data.get("zone_id", "unknown")

    crime_score = compute_crime_penalty(zone_id, crime_data, time_mult, reference_date)
    lighting_score = 1.0 - zone_attrs.get("lighting_score", 0.5)
    isolation_score = zone_attrs.get("isolation_index", 0.5) * time_mult.get("isolation", 1.0)

    crowd_key = "crowd_density_night" if hour >= 18 else "crowd_density_day"
    crowd_score = 1.0 - zone_attrs.get(crowd_key, 0.5)

    emergency_score = 0.0 if zone_attrs.get("emergency_facility_within_500m") else 0.5
    transit_score = 1.0 - zone_attrs.get("transit_accessibility", 0.5)

    community_penalty = get_community_penalty_for_zone(zone_id, hour)

    raw = (
        weights["crime"] * crime_score +
        weights["lighting"] * lighting_score +
        weights["isolation"] * isolation_score +
        weights["crowd"] * crowd_score +
        weights["emergency"] * emergency_score +
        weights["transit"] * transit_score
    )

    total = raw + community_penalty
    return round(min(max(total, 0.0), 1.0), 4)


def compute_edge_weight(edge_data, zone_attrs, crime_data, hour, mode, user_weights=None, reference_date=None):
    distance = edge_data.get("distance_m", 100)
    safety_penalty = compute_safety_score(edge_data, zone_attrs, crime_data, hour, user_weights, reference_date)

    if mode == "fastest":
        return distance
    elif mode == "safest":
        return distance * (1 + 5 * safety_penalty)
    elif mode == "balanced":
        return distance * (1 + 2 * safety_penalty)
    else:
        return distance


def get_factor_breakdown(edge_data, zone_attrs, crime_data, hour, user_weights=None, reference_date=None):
    weights = dict(user_weights) if user_weights else dict(DEFAULT_WEIGHTS)
    total_w = sum(weights.values())
    if total_w == 0:
        weights = dict(DEFAULT_WEIGHTS)
        total_w = 1.0
    weights = {k: v / total_w for k, v in weights.items()}

    time_mult = get_time_multiplier(hour)
    zone_id = edge_data.get("zone_id", "unknown")

    crime_score = compute_crime_penalty(zone_id, crime_data, time_mult, reference_date)
    lighting_score = 1.0 - zone_attrs.get("lighting_score", 0.5)
    isolation_score = zone_attrs.get("isolation_index", 0.5) * time_mult.get("isolation", 1.0)

    crowd_key = "crowd_density_night" if hour >= 18 else "crowd_density_day"
    crowd_score = 1.0 - zone_attrs.get(crowd_key, 0.5)

    emergency_score = 0.0 if zone_attrs.get("emergency_facility_within_500m") else 0.5
    transit_score = 1.0 - zone_attrs.get("transit_accessibility", 0.5)

    community_penalty = get_community_penalty_for_zone(zone_id, hour)

    return {
        "crime": weights["crime"] * crime_score,
        "lighting": weights["lighting"] * lighting_score,
        "isolation": weights["isolation"] * isolation_score,
        "crowd": weights["crowd"] * crowd_score,
        "emergency": weights["emergency"] * emergency_score,
        "transit": weights["transit"] * transit_score,
        "community": community_penalty * (1.0 if user_weights else 0.15),
    }
