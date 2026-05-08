# Nirbhaya SafeTrack - Explainability Engine

from .time_context import get_time_multiplier

FACTOR_LABELS = {
    "crime": "lower historical incident density",
    "lighting": "better street lighting coverage",
    "isolation": "less isolated surroundings",
    "crowd": "higher pedestrian foot traffic",
    "emergency": "closer proximity to emergency services",
    "transit": "better public transport access",
}

FACTOR_HUMAN = {
    "crime": "fewer reported incidents",
    "lighting": "well-lit streets",
    "isolation": "active, non-isolated areas",
    "crowd": "more people around",
    "emergency": "nearby police stations and hospitals",
    "transit": "good metro and bus connectivity",
}

MODE_LABELS = {
    "fastest": "Fastest",
    "safest": "Safest",
    "balanced": "Balanced",
}

TIME_CONTEXT_DESCRIPTIONS = {
    "dawn": "early morning hours when streets are just waking up",
    "daytime": "daytime with maximum pedestrian activity",
    "evening": "evening commute hours with moderate foot traffic",
    "night": "nighttime when many areas become significantly less safe",
    "late_night": "late night hours when isolation risk peaks",
}


def compute_dominant_factors(route_data):
    if not route_data or "factor_breakdowns" not in route_data:
        return []

    breakdowns = route_data["factor_breakdowns"]
    if not breakdowns:
        return []

    avg_factors = {}
    for factor_name in FACTOR_LABELS.keys():
        values = [f.get(factor_name, 0) for f in breakdowns]
        avg_factors[factor_name] = sum(values) / len(values)

    sorted_factors = sorted(avg_factors.keys(), key=lambda f: avg_factors[f])
    return sorted_factors


def compute_risk_zones(route_data, datasets=None):
    if not route_data or "factor_breakdowns" not in route_data:
        return []

    breakdowns = route_data["factor_breakdowns"]
    risk_segments = []

    for i, breakdown in enumerate(breakdowns):
        total = sum(breakdown.values())
        if total > 0.4:
            risk_segments.append({
                "index": i,
                "score": total,
                "top_factor": max(breakdown, key=breakdown.get),
            })

    return risk_segments


def generate_explanation(route_data, alternative_data, mode, time_period_label="night"):
    dominant_factors = compute_dominant_factors(route_data)
    safety_score = route_data.get("safety_score", 0)
    risk_zones = compute_risk_zones(route_data)

    if not dominant_factors:
        return "This route has a balanced safety profile across all factors."

    top_factors = dominant_factors[:2]
    top_human = [FACTOR_HUMAN[f] for f in top_factors]

    if safety_score < 0.15:
        safety_level = "exceptionally safe"
        confidence = "very high"
    elif safety_score < 0.25:
        safety_level = "very safe"
        confidence = "high"
    elif safety_score < 0.35:
        safety_level = "safe"
        confidence = "high"
    elif safety_score < 0.5:
        safety_level = "moderately safe"
        confidence = "medium"
    else:
        safety_level = "caution advised"
        confidence = "low"

    time_desc = TIME_CONTEXT_DESCRIPTIONS.get(time_period_label, "this time")

    base_explanation = (
        f"This {MODE_LABELS.get(mode, mode).lower()} route is rated {safety_level} "
        f"({confidence} confidence) for {time_desc}. "
        f"It prioritizes {' and '.join(top_human)}."
    )

    if risk_zones:
        high_risk_count = len([z for z in risk_zones if z["score"] > 0.5])
        if high_risk_count > 0:
            worst_factor = max(risk_zones, key=lambda z: z["score"])
            base_explanation += f" Note: {high_risk_count} segment{'s' if high_risk_count > 1 else ''} along this route {'has' if high_risk_count == 1 else 'have'} elevated {FACTOR_HUMAN.get(worst_factor['top_factor'], 'risk')}."

    if mode == "balanced":
        fastest_dist = alternative_data.get("fastest", {}).get("distance_m", 0)
        balanced_dist = route_data.get("distance_m", 0)
        if fastest_dist > 0 and balanced_dist > 0:
            extra_pct = ((balanced_dist - fastest_dist) / fastest_dist) * 100
            if extra_pct > 5:
                base_explanation += f" This route adds {extra_pct:.0f}% to travel time compared to the fastest option, but significantly improves safety."
            else:
                base_explanation += f" This route is nearly as fast as the fastest option (only {extra_pct:.0f}% longer) while offering better safety."
    elif mode == "safest":
        fastest_dist = alternative_data.get("fastest", {}).get("distance_m", 0)
        safest_dist = route_data.get("distance_m", 0)
        if fastest_dist > 0 and safest_dist > 0:
            extra_pct = ((safest_dist - fastest_dist) / fastest_dist) * 100
            if extra_pct > 20:
                base_explanation += f" The trade-off is a {extra_pct:.0f}% longer distance for maximum safety assurance."
            elif extra_pct > 0:
                base_explanation += f" At only {extra_pct:.0f}% longer than the fastest route, this is a highly efficient safe option."

    if mode != "fastest":
        fastest_safety = alternative_data.get("fastest", {}).get("safety_score", 0.5)
        if fastest_safety > safety_score + 0.05:
            improvement = round((fastest_safety - safety_score) * 100)
            base_explanation += f" Compared to the fastest route, this path reduces risk by {improvement} percentage points."

    return base_explanation


def generate_route_summary(route_data, mode, node_names=None):
    if node_names is None:
        node_names = {}

    path = route_data.get("path", [])
    if not path:
        return {"error": "No route found"}

    route_nodes = [node_names.get(n, n) for n in path]

    return {
        "mode": MODE_LABELS.get(mode, mode),
        "path_names": route_nodes,
        "distance_m": route_data.get("distance_m", 0),
        "safety_score": route_data.get("safety_score", 0),
        "estimated_walk_time_min": round(route_data.get("distance_m", 0) / 80, 1),
    }
