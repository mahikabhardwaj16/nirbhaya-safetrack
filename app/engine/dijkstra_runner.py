# Nirbhaya SafeTrack - Multi-Objective Dijkstra Pathfinding

import networkx as nx
from .safety_scorer import compute_edge_weight, get_factor_breakdown


def run_dijkstra(graph, source, target, weight_key="weight"):
    try:
        node_ids = nx.shortest_path(graph, source=source, target=target, weight=weight_key)
    except nx.NodeNotFound as e:
        raise ValueError(f"Node not found in graph: {e}")
    except nx.NetworkXNoPath:
        raise ValueError(f"No path exists between {source} and {target}")

    coordinates = [
        {
            "node_id": nid,
            "lat": graph.nodes[nid]["lat"],
            "lon": graph.nodes[nid]["lon"],
            "name": graph.nodes[nid].get("name", nid),
        }
        for nid in node_ids
    ]

    total_weight = sum(
        graph[node_ids[i]][node_ids[i + 1]][weight_key]
        for i in range(len(node_ids) - 1)
    )

    return {
        "node_ids": node_ids,
        "coordinates": coordinates,
        "total_weight": round(total_weight, 4),
        "hop_count": len(node_ids) - 1,
    }


def build_weighted_graph(base_graph, mode, hour, user_weights=None, datasets=None):
    G = base_graph.copy()

    if datasets:
        zone_attrs = datasets["zone_attributes"]
        crime_data = datasets["crime_incidents"]
    else:
        zone_attrs = {}
        crime_data = []

    node_to_zone = {}
    for nid, ndata in G.nodes(data=True):
        node_to_zone[nid] = ndata.get("zone_id", "")

    for u, v, d in G.edges(data=True):
        edge_zone = node_to_zone.get(u, "")
        za = zone_attrs.get(edge_zone, {
            "lighting_score": 0.5,
            "crowd_density_night": 0.5,
            "isolation_index": 0.5,
            "emergency_facility_within_500m": False,
            "transit_accessibility": 0.5,
        })
        edge_data = {
            "zone_id": edge_zone,
            "distance_m": d.get("distance_m", 100),
        }
        weight = compute_edge_weight(edge_data, za, crime_data, hour, mode, user_weights)
        G[u][v]["weight"] = weight

    return G


def find_route(G, datasets, origin_id, destination_id, hour, mode, user_weights=None, waypoints=None, reference_date=None):
    zone_attrs = datasets["zone_attributes"]
    crime_data = datasets["crime_incidents"]

    node_to_zone = {}
    for node_id, node_data in G.nodes(data=True):
        node_to_zone[node_id] = node_data.get("zone_id", "")

    def weight_func(u, v, d):
        edge_zone = node_to_zone.get(u, "")
        edge_data = {
            "zone_id": edge_zone,
            "distance_m": d.get("distance_m", 100),
            "road_type": d.get("road_type", "local"),
        }
        za = zone_attrs.get(edge_zone, {
            "lighting_score": 0.5,
            "crowd_density_night": 0.5,
            "isolation_index": 0.5,
            "emergency_facility_within_500m": False,
            "transit_accessibility": 0.5,
        })
        return compute_edge_weight(edge_data, za, crime_data, hour, mode, user_weights, reference_date)

    if waypoints:
        all_nodes = [origin_id] + waypoints + [destination_id]
        full_path = []
        total_distance = 0
        total_safety = 0
        all_factors = []

        for i in range(len(all_nodes) - 1):
            path, distance, safety, factors = _run_single_dijkstra(
                G, all_nodes[i], all_nodes[i + 1], weight_func, node_to_zone,
                zone_attrs, crime_data, hour, mode, user_weights, reference_date
            )
            if path is None:
                return None, None, None, None
            if full_path and path[0] == full_path[-1]:
                path = path[1:]
            full_path.extend(path)
            total_distance += distance
            total_safety += safety
            all_factors.extend(factors)

        avg_safety = total_safety / len(all_factors) if all_factors else 0
        return full_path, total_distance, avg_safety, all_factors
    else:
        return _run_single_dijkstra(
            G, origin_id, destination_id, weight_func, node_to_zone,
            zone_attrs, crime_data, hour, mode, user_weights, reference_date
        )


def _run_single_dijkstra(G, origin_id, destination_id, weight_func, node_to_zone,
                         zone_attrs, crime_data, hour, mode, user_weights, reference_date):
    try:
        path = nx.shortest_path(G, origin_id, destination_id, weight=weight_func)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, None, None, None

    total_distance = 0
    all_factors = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        d = G[u][v]
        edge_zone = node_to_zone.get(u, "")
        edge_data = {
            "zone_id": edge_zone,
            "distance_m": d.get("distance_m", 100),
        }
        za = zone_attrs.get(edge_zone, {
            "lighting_score": 0.5,
            "crowd_density_night": 0.5,
            "isolation_index": 0.5,
            "emergency_facility_within_500m": False,
            "transit_accessibility": 0.5,
        })

        total_distance += d.get("distance_m", 100)
        factors = get_factor_breakdown(edge_data, za, crime_data, hour, user_weights, reference_date)
        all_factors.append(factors)

    avg_safety = sum(sum(f.values()) for f in all_factors) / len(all_factors) if all_factors else 0

    return path, total_distance, avg_safety, all_factors


def find_all_routes(G, datasets, origin_id, destination_id, hour, user_weights=None, waypoints=None, reference_date=None):
    results = {}
    for mode in ["fastest", "safest", "balanced"]:
        path, distance, safety, factors = find_route(
            G, datasets, origin_id, destination_id, hour, mode,
            user_weights, waypoints, reference_date
        )
        if path:
            coordinates = [
                {
                    "node_id": nid,
                    "lat": G.nodes[nid].get("lat"),
                    "lon": G.nodes[nid].get("lon"),
                    "name": G.nodes[nid].get("name", nid),
                }
                for nid in path
            ]
            results[mode] = {
                "path": path,
                "distance_m": distance,
                "safety_score": round(safety, 3),
                "factor_breakdowns": factors,
                "coordinates": coordinates,
            }
    return results
