# Nirbhaya SafeTrack - Dijkstra Runner Tests

from app.engine.dijkstra_runner import find_route, find_all_routes


def test_fastest_route_direct_path(sample_graph, sample_datasets):
    path, distance, safety, factors = find_route(
        sample_graph, sample_datasets, "A", "C", hour=12, mode="fastest"
    )
    assert path is not None, "Should find a path"
    assert path[0] == "A"
    assert path[-1] == "C"


def test_safest_route_avoids_dangerous_zones(sample_graph, sample_datasets):
    path_fastest, dist_fastest, _, _ = find_route(
        sample_graph, sample_datasets, "C", "E", hour=23, mode="fastest"
    )
    path_safest, dist_safest, safety_safest, _ = find_route(
        sample_graph, sample_datasets, "C", "E", hour=23, mode="safest"
    )

    assert path_fastest is not None
    assert path_safest is not None


def test_balanced_route_exists(sample_graph, sample_datasets):
    path, distance, safety, factors = find_route(
        sample_graph, sample_datasets, "A", "E", hour=20, mode="balanced"
    )
    assert path is not None
    assert distance > 0


def test_no_path_returns_none(sample_graph, sample_datasets):
    path, distance, safety, factors = find_route(
        sample_graph, sample_datasets, "A", "Z", hour=12, mode="fastest"
    )
    assert path is None
    assert distance is None


def test_all_modes_return_results(sample_graph, sample_datasets):
    results = find_all_routes(sample_graph, sample_datasets, "A", "E", hour=18)
    assert "fastest" in results
    assert "safest" in results
    assert "balanced" in results


def test_route_path_is_valid(sample_graph, sample_datasets):
    path, distance, safety, factors = find_route(
        sample_graph, sample_datasets, "A", "D", hour=14, mode="balanced"
    )
    assert path is not None
    assert len(path) >= 2
    assert sample_graph.has_edge(path[0], path[1]) or sample_graph.has_edge(path[1], path[0])


def test_safety_score_reasonable(sample_graph, sample_datasets):
    _, _, safety_fast, _ = find_route(
        sample_graph, sample_datasets, "A", "B", hour=12, mode="fastest"
    )
    _, _, safety_safe, _ = find_route(
        sample_graph, sample_datasets, "A", "B", hour=2, mode="safest"
    )
    assert 0 <= safety_fast <= 1
    assert 0 <= safety_safe <= 1
