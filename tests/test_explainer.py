# Nirbhaya SafeTrack - Explainer Tests

from app.engine.explainer import generate_explanation, compute_dominant_factors, generate_route_summary


def test_explanation_contains_factor_labels():
    route_data = {
        "path": ["A", "B", "C"],
        "distance_m": 500,
        "safety_score": 0.25,
        "factor_breakdowns": [
            {"crime": 0.02, "lighting": 0.03, "isolation": 0.05, "crowd": 0.02, "emergency": 0.01, "transit": 0.02},
        ],
    }

    explanation = generate_explanation(route_data, {}, "safest", "night")
    assert "police stations" in explanation or "reported incidents" in explanation or "safe" in explanation


def test_explanation_for_balanced_mode_includes_time():
    route_data = {
        "path": ["A", "B", "C"],
        "distance_m": 600,
        "safety_score": 0.35,
        "factor_breakdowns": [
            {"crime": 0.03, "lighting": 0.02, "isolation": 0.04, "crowd": 0.01, "emergency": 0.02, "transit": 0.03},
        ],
    }

    alternatives = {"fastest": {"distance_m": 400, "safety_score": 0.6}}
    explanation = generate_explanation(route_data, alternatives, "balanced", "evening")
    assert "travel time" in explanation.lower() or "longer" in explanation.lower()


def test_dominant_factors_sorted_by_lowest():
    route_data = {
        "factor_breakdowns": [
            {"crime": 0.10, "lighting": 0.02, "isolation": 0.08, "crowd": 0.01, "emergency": 0.03, "transit": 0.05},
        ],
    }

    factors = compute_dominant_factors(route_data)
    assert factors[0] == "crowd", f"Expected crowd to be lowest, got {factors[0]}"


def test_empty_route_data_returns_default():
    explanation = generate_explanation({}, {}, "fastest", "daytime")
    assert "balanced" in explanation.lower()


def test_route_summary_structure():
    route_data = {
        "path": ["A", "B", "C"],
        "distance_m": 800,
        "safety_score": 0.3,
        "factor_breakdowns": [],
    }

    summary = generate_route_summary(route_data, "safest", {"A": "Start", "B": "Mid", "C": "End"})
    assert summary["mode"] == "Safest"
    assert summary["distance_m"] == 800
    assert summary["estimated_walk_time_min"] == 10.0


def test_explanation_varies_by_time_period():
    route_data = {
        "path": ["A", "B"],
        "distance_m": 300,
        "safety_score": 0.4,
        "factor_breakdowns": [
            {"crime": 0.05, "lighting": 0.04, "isolation": 0.06, "crowd": 0.02, "emergency": 0.02, "transit": 0.03},
        ],
    }

    exp_day = generate_explanation(route_data, {}, "safest", "daytime")
    exp_night = generate_explanation(route_data, {}, "safest", "late_night")
    assert "daytime" in exp_day
    assert "late night" in exp_night
