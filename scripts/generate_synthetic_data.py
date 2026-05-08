#!/usr/bin/env python3
# Nirbhaya SafeTrack - Synthetic Data Generator

import json
import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

BASE_LAT = 28.6100
BASE_LON = 77.1980
GRID_SIZE = 0.04
NUM_NODES = 40
NUM_ZONES = 15

ROAD_TYPES = ["arterial", "subarterial", "local"]
CRIME_TYPES = ["harassment", "theft", "assault", "robbery", "kidnapping"]
CRIME_WEIGHTS = [0.35, 0.25, 0.20, 0.15, 0.05]
FACILITY_TYPES = ["police_station", "hospital", "emergency_helpdesk"]


def generate_nodes():
    nodes = []
    zone_ids = [f"Z{str(i).zfill(3)}" for i in range(1, NUM_ZONES + 1)]

    for i in range(NUM_NODES):
        lat = BASE_LAT + random.uniform(0, GRID_SIZE)
        lon = BASE_LON + random.uniform(0, GRID_SIZE)
        zone = random.choice(zone_ids)
        nodes.append({
            "id": f"N{str(i + 1).zfill(3)}",
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "zone_id": zone,
            "name": f"Location {i + 1}",
        })
    return nodes


def generate_edges(nodes):
    edges = []
    edge_id = 1
    for i in range(len(nodes) - 1):
        for j in range(i + 1, min(i + 4, len(nodes))):
            if random.random() < 0.5:
                dist = int(random.uniform(100, 600))
                edges.append({
                    "id": f"E{str(edge_id).zfill(3)}",
                    "source": nodes[i]["id"],
                    "target": nodes[j]["id"],
                    "distance_m": dist,
                    "road_type": random.choice(ROAD_TYPES),
                    "has_streetlight": random.random() > 0.3,
                    "transit_stops_nearby": random.randint(0, 5),
                })
                edge_id += 1
    return edges


def generate_zone_attributes():
    zones = {}
    for i in range(1, NUM_ZONES + 1):
        zone_id = f"Z{str(i).zfill(3)}"
        zones[zone_id] = {
            "lighting_score": round(random.uniform(0.2, 0.95), 2),
            "crowd_density_day": round(random.uniform(0.1, 0.95), 2),
            "crowd_density_night": round(random.uniform(0.05, 0.7), 2),
            "isolation_index": round(random.uniform(0.1, 0.9), 2),
            "emergency_facility_within_500m": random.random() > 0.5,
            "transit_accessibility": round(random.uniform(0.1, 0.95), 2),
        }
    return zones


def generate_crime_incidents(num_incidents=60):
    zone_ids = [f"Z{str(i).zfill(3)}" for i in range(1, NUM_ZONES + 1)]
    incidents = []
    start_date = datetime(2024, 6, 1)

    for i in range(num_incidents):
        zone = random.choice(zone_ids)
        crime_type = random.choices(CRIME_TYPES, weights=CRIME_WEIGHTS, k=1)[0]
        severity = {"harassment": 3, "theft": 4, "assault": 7, "robbery": 8, "kidnapping": 10}[crime_type]
        timestamp = start_date + timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        incidents.append({
            "incident_id": f"INC{str(i + 1).zfill(3)}",
            "zone_id": zone,
            "type": crime_type,
            "severity": severity,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M"),
            "lat": round(BASE_LAT + random.uniform(0, GRID_SIZE), 3),
            "lon": round(BASE_LON + random.uniform(0, GRID_SIZE), 3),
        })
    return incidents


def generate_emergency_facilities(num_facilities=12):
    facilities = []
    for i in range(num_facilities):
        ftype = random.choice(FACILITY_TYPES)
        facilities.append({
            "facility_id": f"F{str(i + 1).zfill(3)}",
            "type": ftype,
            "lat": round(BASE_LAT + random.uniform(0, GRID_SIZE), 3),
            "lon": round(BASE_LON + random.uniform(0, GRID_SIZE), 3),
            "name": f"{ftype.replace('_', ' ').title()} {i + 1}",
            "operational_24h": random.random() > 0.3,
        })
    return facilities


def save_data(data_dir):
    os.makedirs(data_dir, exist_ok=True)

    nodes = generate_nodes()
    edges = generate_edges(nodes)

    road_segments = {"nodes": nodes, "edges": edges}
    with open(os.path.join(data_dir, "road_segments.json"), "w") as f:
        json.dump(road_segments, f, indent=2)

    zone_attrs = generate_zone_attributes()
    with open(os.path.join(data_dir, "zone_attributes.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "zone_id", "lighting_score", "crowd_density_day", "crowd_density_night",
            "isolation_index", "emergency_facility_within_500m", "transit_accessibility",
        ])
        writer.writeheader()
        for zone_id, attrs in zone_attrs.items():
            row = {"zone_id": zone_id, **attrs}
            writer.writerow(row)

    incidents = generate_crime_incidents()
    with open(os.path.join(data_dir, "crime_incidents.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "incident_id", "zone_id", "type", "severity", "timestamp", "lat", "lon",
        ])
        writer.writeheader()
        writer.writerows(incidents)

    facilities = generate_emergency_facilities()
    with open(os.path.join(data_dir, "emergency_facilities.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "facility_id", "type", "lat", "lon", "name", "operational_24h",
        ])
        writer.writeheader()
        writer.writerows(facilities)

    print(f"Generated synthetic data in {data_dir}:")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Zones: {len(zone_attrs)}")
    print(f"  Crime incidents: {len(incidents)}")
    print(f"  Emergency facilities: {len(facilities)}")


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data")
    save_data(data_dir)
