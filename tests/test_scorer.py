# Nirbhaya SafeTrack - Safety Scorer Tests

from app.engine.safety_scorer import compute_safety_score, compute_edge_weight, get_factor_breakdown
from app.engine.time_context import get_time_multiplier


def test_high_crime_night_poor_lighting(sample_datasets):
    zone_attrs = sample_datasets["zone_attributes"]["Z3"]
    crime_data = sample_datasets["crime_incidents"]
    edge_data = {"zone_id": "Z3"}

    score_night = compute_safety_score(edge_data, zone_attrs, crime_data, hour=23)
    assert score_night > 0.5, f"Expected high danger score for dark, high-crime zone at night, got {score_night}"


def test_well_lit_daytime_safe_zone(sample_datasets):
    zone_attrs = sample_datasets["zone_attributes"]["Z1"]
    crime_data = sample_datasets["crime_incidents"]
    edge_data = {"zone_id": "Z1"}

    score_day = compute_safety_score(edge_data, zone_attrs, crime_data, hour=12)
    assert score_day < 0.5, f"Expected low danger score for well-lit safe zone during day, got {score_day}"


def test_time_multiplier_dawn():
    mult = get_time_multiplier(6)
    assert mult["label"] == "dawn"
    assert mult["crime"] == 0.5
    assert mult["isolation"] == 0.4


def test_time_multiplier_night():
    mult = get_time_multiplier(23)
    assert mult["label"] == "night"
    assert mult["crime"] == 1.0
    assert mult["isolation"] == 1.0


def test_time_multiplier_late_night():
    mult = get_time_multiplier(2)
    assert mult["label"] == "late_night"
    assert mult["crime"] == 1.2


def test_edge_weight_fastest_mode(sample_datasets):
    zone_attrs = sample_datasets["zone_attributes"]["Z1"]
    crime_data = sample_datasets["crime_incidents"]
    edge_data = {"zone_id": "Z1", "distance_m": 200}

    weight = compute_edge_weight(edge_data, zone_attrs, crime_data, hour=14, mode="fastest")
    assert weight == 200, "Fastest mode should return pure distance"


def test_edge_weight_safest_mode(sample_datasets):
    zone_attrs = sample_datasets["zone_attributes"]["Z3"]
    crime_data = sample_datasets["crime_incidents"]
    edge_data = {"zone_id": "Z3", "distance_m": 300}

    weight = compute_edge_weight(edge_data, zone_attrs, crime_data, hour=23, mode="safest")
    assert weight > 300, "Safest mode should add penalty to dangerous edges"


def test_factor_breakdown_returns_all_factors(sample_datasets):
    zone_attrs = sample_datasets["zone_attributes"]["Z2"]
    crime_data = sample_datasets["crime_incidents"]
    edge_data = {"zone_id": "Z2"}

    factors = get_factor_breakdown(edge_data, zone_attrs, crime_data, hour=20)
    expected_keys = {"crime", "lighting", "isolation", "crowd", "emergency", "transit", "community"}
    assert set(factors.keys()) == expected_keys


def test_score_bounds(sample_datasets):
    zone_attrs = sample_datasets["zone_attributes"]["Z3"]
    crime_data = sample_datasets["crime_incidents"]
    edge_data = {"zone_id": "Z3"}

    for hour in range(24):
        score = compute_safety_score(edge_data, zone_attrs, crime_data, hour)
        assert 0.0 <= score <= 1.0, f"Score out of bounds at hour {hour}: {score}"
