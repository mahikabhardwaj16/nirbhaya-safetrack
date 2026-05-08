# Nirbhaya SafeTrack - Graph Builder

import networkx as nx


def build_graph(datasets):
    road_segments = datasets["road_segments"]

    G = nx.DiGraph()

    for node in road_segments["nodes"]:
        G.add_node(
            node["id"],
            lat=node["lat"],
            lon=node["lon"],
            zone_id=node["zone_id"],
            name=node["name"],
        )

    for edge in road_segments["edges"]:
        G.add_edge(
            edge["source"],
            edge["target"],
            edge_id=edge["id"],
            distance_m=edge["distance_m"],
            road_type=edge["road_type"],
            has_streetlight=edge["has_streetlight"],
            transit_stops_nearby=edge["transit_stops_nearby"],
        )

    for edge in road_segments["edges"]:
        if not G.has_edge(edge["target"], edge["source"]):
            G.add_edge(
                edge["target"],
                edge["source"],
                edge_id=edge["id"] + "_rev",
                distance_m=edge["distance_m"],
                road_type=edge["road_type"],
                has_streetlight=edge["has_streetlight"],
                transit_stops_nearby=edge["transit_stops_nearby"],
            )

    return G
