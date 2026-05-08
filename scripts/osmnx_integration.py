# Nirbhaya SafeTrack - OSMnx Integration Script
# Pulls real road network from OpenStreetMap and converts to SafeTrack format

import json
import os

try:
    import osmnx as ox
    import networkx as nx
    HAS_OSMNX = True
except ImportError:
    HAS_OSMNX = False
    print("OSMnx not installed. Install with: pip install osmnx")


def pull_osm_graph(place_name, graph_type="drive", filepath=None):
    if not HAS_OSMNX:
        print("Error: OSMnx is required. Install with: pip install osmnx")
        return None

    print(f"Pulling road network for: {place_name}")
    G = ox.graph_from_place(place_name, network_type=graph_type)
    print(f"  Retrieved graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    G_proj = ox.project_graph(G)

    nodes = []
    node_id_map = {}
    for i, (osm_id, data) in enumerate(G.nodes(data=True)):
        new_id = f"N{str(i + 1).zfill(4)}"
        node_id_map[osm_id] = new_id

        lat = data.get("y", 0)
        lon = data.get("x", 0)

        nodes.append({
            "id": new_id,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "zone_id": f"Z{str((i % 20) + 1).zfill(3)}",
            "name": f"Node {i + 1}",
        })

    edges = []
    edge_id = 1
    for u, v, data in G.edges(data=True):
        if u not in node_id_map or v not in node_id_map:
            continue

        length = data.get("length", 100)
        highway = data.get("highway", "residential")

        road_type = "arterial" if highway in ["primary", "trunk", "motorway"] else \
                    "subarterial" if highway in ["secondary", "tertiary"] else "local"

        edges.append({
            "id": f"E{str(edge_id).zfill(4)}",
            "source": node_id_map[u],
            "target": node_id_map[v],
            "distance_m": int(length),
            "road_type": road_type,
            "has_streetlight": highway in ["primary", "trunk", "motorway", "secondary"],
            "transit_stops_nearby": 0,
        })
        edge_id += 1

    graph_data = {"nodes": nodes, "edges": edges}

    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(graph_data, f, indent=2)
        print(f"  Saved to: {filepath}")

    return graph_data


def pull_osm_graph_by_coords(center_lat, center_lon, dist_meters=1000, filepath=None):
    if not HAS_OSMNX:
        print("Error: OSMnx is required. Install with: pip install osmnx")
        return None

    print(f"Pulling road network near ({center_lat}, {center_lon}) within {dist_meters}m")
    G = ox.graph_from_point((center_lat, center_lon), dist=dist_meters, network_type="drive")
    print(f"  Retrieved graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    return pull_osm_graph_impl(G, filepath)


def pull_osm_graph_impl(G, filepath=None):
    nodes = []
    node_id_map = {}
    for i, (osm_id, data) in enumerate(G.nodes(data=True)):
        new_id = f"N{str(i + 1).zfill(4)}"
        node_id_map[osm_id] = new_id

        lat = data.get("y", 0)
        lon = data.get("x", 0)

        nodes.append({
            "id": new_id,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "zone_id": f"Z{str((i % 20) + 1).zfill(3)}",
            "name": f"Node {i + 1}",
        })

    edges = []
    edge_id = 1
    for u, v, data in G.edges(data=True):
        if u not in node_id_map or v not in node_id_map:
            continue

        length = data.get("length", 100)
        highway = data.get("highway", "residential")

        road_type = "arterial" if highway in ["primary", "trunk", "motorway"] else \
                    "subarterial" if highway in ["secondary", "tertiary"] else "local"

        edges.append({
            "id": f"E{str(edge_id).zfill(4)}",
            "source": node_id_map[u],
            "target": node_id_map[v],
            "distance_m": int(length),
            "road_type": road_type,
            "has_streetlight": highway in ["primary", "trunk", "motorway", "secondary"],
            "transit_stops_nearby": 0,
        })
        edge_id += 1

    graph_data = {"nodes": nodes, "edges": edges}

    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(graph_data, f, indent=2)
        print(f"  Saved to: {filepath}")

    print(f"  Nodes: {len(nodes)}, Edges: {len(edges)}")
    return graph_data


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        place = " ".join(sys.argv[1:])
        data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data")
        filepath = os.path.join(data_dir, "road_segments.json")
        pull_osm_graph(place, filepath=filepath)
    else:
        print("Usage: python osmnx_integration.py <place name>")
        print("Examples:")
        print("  python osmnx_integration.py Connaught Place, New Delhi, India")
        print("  python osmnx_integration.py Chandigarh, India")
        print("  python osmnx_integration.py Koramangala, Bangalore, India")
