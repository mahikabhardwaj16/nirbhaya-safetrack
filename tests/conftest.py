# Nirbhaya SafeTrack - Test Fixtures

import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.graph_builder import build_graph
from app.engine.time_context import get_time_multiplier
from app.engine.safety_scorer import compute_safety_score, compute_edge_weight
from app.engine.explainer import generate_explanation, compute_dominant_factors


RECENT = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M")
OLD = (datetime.now() - timedelta(hours=200)).strftime("%Y-%m-%d %H:%M")


@pytest.fixture
def sample_datasets():
    return {
        "road_segments": {
            "nodes": [
                {"id": "A", "lat": 0, "lon": 0, "zone_id": "Z1", "name": "Node A"},
                {"id": "B", "lat": 1, "lon": 1, "zone_id": "Z1", "name": "Node B"},
                {"id": "C", "lat": 2, "lon": 2, "zone_id": "Z2", "name": "Node C"},
                {"id": "D", "lat": 3, "lon": 3, "zone_id": "Z2", "name": "Node D"},
                {"id": "E", "lat": 4, "lon": 4, "zone_id": "Z3", "name": "Node E"},
            ],
            "edges": [
                {"id": "AB", "source": "A", "target": "B", "distance_m": 100, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
                {"id": "BC", "source": "B", "target": "C", "distance_m": 200, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 1},
                {"id": "AC", "source": "A", "target": "C", "distance_m": 500, "road_type": "local", "has_streetlight": False, "transit_stops_nearby": 0},
                {"id": "CD", "source": "C", "target": "D", "distance_m": 150, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 3},
                {"id": "DE", "source": "D", "target": "E", "distance_m": 300, "road_type": "subarterial", "has_streetlight": False, "transit_stops_nearby": 0},
                {"id": "CE", "source": "C", "target": "E", "distance_m": 250, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
            ],
        },
        "zone_attributes": {
            "Z1": {"lighting_score": 0.9, "crowd_density_day": 0.8, "crowd_density_night": 0.6, "isolation_index": 0.1, "emergency_facility_within_500m": True, "transit_accessibility": 0.9},
            "Z2": {"lighting_score": 0.5, "crowd_density_day": 0.4, "crowd_density_night": 0.2, "isolation_index": 0.6, "emergency_facility_within_500m": False, "transit_accessibility": 0.4},
            "Z3": {"lighting_score": 0.2, "crowd_density_day": 0.1, "crowd_density_night": 0.05, "isolation_index": 0.9, "emergency_facility_within_500m": False, "transit_accessibility": 0.1},
        },
        "crime_incidents": [
            {"zone_id": "Z3", "type": "assault", "severity": 7, "timestamp": RECENT, "lat": 4, "lon": 4},
            {"zone_id": "Z3", "type": "robbery", "severity": 8, "timestamp": RECENT, "lat": 4, "lon": 4},
            {"zone_id": "Z1", "type": "theft", "severity": 4, "timestamp": OLD, "lat": 0, "lon": 0},
        ],
        "emergency_facilities": [],
    }


@pytest.fixture
def sample_graph(sample_datasets):
    return build_graph(sample_datasets)
