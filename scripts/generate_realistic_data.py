# Nirbhaya SafeTrack - Realistic Incident Data Generator

import json
import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

BASE_LAT = 28.6139
BASE_LON = 77.2090

ZONE_PROFILES = {
    "Z012": {"name": "Connaught Place", "type": "commercial", "lighting": 0.9, "crowd_day": 0.95, "crowd_night": 0.6, "isolation": 0.05, "emergency": True, "transit": 0.95},
    "Z015": {"name": "Kasturba Gandhi Marg", "type": "commercial", "lighting": 0.85, "crowd_day": 0.85, "crowd_night": 0.4, "isolation": 0.15, "emergency": True, "transit": 0.85},
    "Z018": {"name": "Parliament Street", "type": "government", "lighting": 0.9, "crowd_day": 0.7, "crowd_night": 0.2, "isolation": 0.25, "emergency": True, "transit": 0.8},
    "Z020": {"name": "India Gate", "type": "tourist", "lighting": 0.7, "crowd_day": 0.8, "crowd_night": 0.3, "isolation": 0.4, "emergency": False, "transit": 0.4},
    "Z013": {"name": "Tolstoy Marg", "type": "mixed", "lighting": 0.5, "crowd_day": 0.5, "crowd_night": 0.2, "isolation": 0.55, "emergency": False, "transit": 0.5},
    "Z010": {"name": "Patel Chowk", "type": "government", "lighting": 0.75, "crowd_day": 0.6, "crowd_night": 0.15, "isolation": 0.35, "emergency": True, "transit": 0.7},
    "Z008": {"name": "Rajpath West", "type": "open", "lighting": 0.3, "crowd_day": 0.3, "crowd_night": 0.05, "isolation": 0.85, "emergency": False, "transit": 0.1},
    "Z022": {"name": "Rajiv Chowk Metro", "type": "transit", "lighting": 0.9, "crowd_day": 0.9, "crowd_night": 0.5, "isolation": 0.1, "emergency": True, "transit": 0.95},
    "Z025": {"name": "Ramakrishna Ashram Marg", "type": "transit", "lighting": 0.4, "crowd_day": 0.6, "crowd_night": 0.2, "isolation": 0.7, "emergency": False, "transit": 0.3},
    "Z019": {"name": "ITO Crossing", "type": "commercial", "lighting": 0.6, "crowd_day": 0.7, "crowd_night": 0.15, "isolation": 0.45, "emergency": False, "transit": 0.5},
    "Z021": {"name": "Supreme Court", "type": "government", "lighting": 0.5, "crowd_day": 0.4, "crowd_night": 0.1, "isolation": 0.65, "emergency": True, "transit": 0.3},
    "Z016": {"name": "Shivaji Stadium", "type": "transit", "lighting": 0.7, "crowd_day": 0.65, "crowd_night": 0.25, "isolation": 0.35, "emergency": True, "transit": 0.75},
}

NODES = [
    {"id": "N001", "lat": 28.6139, "lon": 77.2090, "zone_id": "Z012", "name": "Connaught Place Junction"},
    {"id": "N002", "lat": 28.6155, "lon": 77.2120, "zone_id": "Z012", "name": "Barakhamba Road"},
    {"id": "N003", "lat": 28.6180, "lon": 77.2150, "zone_id": "Z015", "name": "Kasturba Gandhi Marg"},
    {"id": "N004", "lat": 28.6200, "lon": 77.2180, "zone_id": "Z015", "name": "Janpath Crossing"},
    {"id": "N005", "lat": 28.6225, "lon": 77.2210, "zone_id": "Z018", "name": "Parliament Street"},
    {"id": "N006", "lat": 28.6250, "lon": 77.2240, "zone_id": "Z018", "name": "Mandi House"},
    {"id": "N007", "lat": 28.6270, "lon": 77.2270, "zone_id": "Z020", "name": "India Gate Circle"},
    {"id": "N008", "lat": 28.6200, "lon": 77.2100, "zone_id": "Z013", "name": "Tolstoy Marg"},
    {"id": "N009", "lat": 28.6175, "lon": 77.2070, "zone_id": "Z013", "name": "Krishna Menon Marg"},
    {"id": "N010", "lat": 28.6150, "lon": 77.2040, "zone_id": "Z010", "name": "Patel Chowk"},
    {"id": "N011", "lat": 28.6125, "lon": 77.2010, "zone_id": "Z010", "name": "Udyog Bhawan"},
    {"id": "N012", "lat": 28.6100, "lon": 77.1980, "zone_id": "Z008", "name": "Rajpath West"},
    {"id": "N013", "lat": 28.6280, "lon": 77.2150, "zone_id": "Z022", "name": "Rajiv Chowk Metro"},
    {"id": "N014", "lat": 28.6300, "lon": 77.2180, "zone_id": "Z022", "name": "Paharganj Road"},
    {"id": "N015", "lat": 28.6320, "lon": 77.2210, "zone_id": "Z025", "name": "Ramakrishna Ashram Marg"},
    {"id": "N016", "lat": 28.6160, "lon": 77.2250, "zone_id": "Z019", "name": "ITO Crossing"},
    {"id": "N017", "lat": 28.6140, "lon": 77.2280, "zone_id": "Z019", "name": "Pragati Maidan"},
    {"id": "N018", "lat": 28.6110, "lon": 77.2310, "zone_id": "Z021", "name": "Supreme Court"},
    {"id": "N019", "lat": 28.6240, "lon": 77.2120, "zone_id": "Z016", "name": "Shivaji Stadium"},
    {"id": "N020", "lat": 28.6260, "lon": 77.2090, "zone_id": "Z016", "name": "Patel Road"},
]

EDGES = [
    {"id": "E001", "source": "N001", "target": "N002", "distance_m": 340, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
    {"id": "E002", "source": "N002", "target": "N003", "distance_m": 420, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 3},
    {"id": "E003", "source": "N003", "target": "N004", "distance_m": 310, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E004", "source": "N004", "target": "N005", "distance_m": 290, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
    {"id": "E005", "source": "N005", "target": "N006", "distance_m": 380, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 4},
    {"id": "E006", "source": "N006", "target": "N007", "distance_m": 270, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E007", "source": "N001", "target": "N008", "distance_m": 520, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E008", "source": "N008", "target": "N009", "distance_m": 350, "road_type": "local", "has_streetlight": False, "transit_stops_nearby": 0},
    {"id": "E009", "source": "N009", "target": "N010", "distance_m": 380, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
    {"id": "E010", "source": "N010", "target": "N011", "distance_m": 310, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E011", "source": "N011", "target": "N012", "distance_m": 450, "road_type": "subarterial", "has_streetlight": False, "transit_stops_nearby": 0},
    {"id": "E012", "source": "N001", "target": "N013", "distance_m": 480, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 5},
    {"id": "E013", "source": "N013", "target": "N014", "distance_m": 290, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 2},
    {"id": "E014", "source": "N014", "target": "N015", "distance_m": 360, "road_type": "local", "has_streetlight": False, "transit_stops_nearby": 0},
    {"id": "E015", "source": "N002", "target": "N016", "distance_m": 540, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 3},
    {"id": "E016", "source": "N016", "target": "N017", "distance_m": 320, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E017", "source": "N017", "target": "N018", "distance_m": 410, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E018", "source": "N003", "target": "N019", "distance_m": 370, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 3},
    {"id": "E019", "source": "N019", "target": "N020", "distance_m": 260, "road_type": "local", "has_streetlight": False, "transit_stops_nearby": 0},
    {"id": "E020", "source": "N020", "target": "N014", "distance_m": 430, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 1},
    {"id": "E021", "source": "N004", "target": "N006", "distance_m": 350, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
    {"id": "E022", "source": "N007", "target": "N018", "distance_m": 490, "road_type": "subarterial", "has_streetlight": True, "transit_stops_nearby": 0},
    {"id": "E023", "source": "N005", "target": "N013", "distance_m": 310, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 3},
    {"id": "E024", "source": "N009", "target": "N019", "distance_m": 440, "road_type": "local", "has_streetlight": False, "transit_stops_nearby": 0},
    {"id": "E025", "source": "N016", "target": "N007", "distance_m": 380, "road_type": "arterial", "has_streetlight": True, "transit_stops_nearby": 2},
]

CRIME_PATTERNS = {
    "commercial": {"harassment": 0.40, "theft": 0.30, "assault": 0.15, "robbery": 0.10, "kidnapping": 0.05},
    "government": {"harassment": 0.25, "theft": 0.20, "assault": 0.30, "robbery": 0.15, "kidnapping": 0.10},
    "tourist": {"harassment": 0.35, "theft": 0.40, "assault": 0.15, "robbery": 0.05, "kidnapping": 0.05},
    "transit": {"harassment": 0.45, "theft": 0.30, "assault": 0.10, "robbery": 0.10, "kidnapping": 0.05},
    "mixed": {"harassment": 0.30, "theft": 0.25, "assault": 0.25, "robbery": 0.15, "kidnapping": 0.05},
    "open": {"harassment": 0.20, "theft": 0.15, "assault": 0.35, "robbery": 0.20, "kidnapping": 0.10},
}

TIME_RISK = {
    0: 1.5, 1: 1.8, 2: 2.0, 3: 2.0, 4: 1.5, 5: 0.8,
    6: 0.5, 7: 0.4, 8: 0.3, 9: 0.3, 10: 0.3, 11: 0.4,
    12: 0.5, 13: 0.5, 14: 0.5, 15: 0.6, 16: 0.8, 17: 1.0,
    18: 1.2, 19: 1.4, 20: 1.5, 21: 1.6, 22: 1.7, 23: 1.6,
}


def generate_realistic_incidents(num_incidents=80):
    incidents = []
    start_date = datetime(2024, 6, 1)
    incident_id = 1

    zone_to_node = {}
    for node in NODES:
        zone_id = node["zone_id"]
        if zone_id not in zone_to_node:
            zone_to_node[zone_id] = []
        zone_to_node[zone_id].append(node)

    for zone_id, profile in ZONE_PROFILES.items():
        zone_type = profile["type"]
        crime_dist = CRIME_PATTERNS.get(zone_type, CRIME_PATTERNS["mixed"])
        crime_types = list(crime_dist.keys())
        crime_weights = list(crime_dist.values())

        base_count = max(3, int(num_incidents / len(ZONE_PROFILES) * (1.5 if zone_type in ["transit", "open"] else 1.0)))

        for _ in range(base_count):
            crime_type = random.choices(crime_types, weights=crime_weights, k=1)[0]
            severity = {"harassment": 3, "theft": 4, "assault": 7, "robbery": 8, "kidnapping": 10}[crime_type]

            hour_weights = [TIME_RISK[h] for h in range(24)]
            hour = random.choices(range(24), weights=hour_weights, k=1)[0]

            days_offset = random.randint(0, 180)
            timestamp = start_date + timedelta(days=days_offset, hours=hour, minutes=random.randint(0, 59))

            nodes_in_zone = zone_to_node.get(zone_id, [])
            if nodes_in_zone:
                ref_node = random.choice(nodes_in_zone)
                lat = ref_node["lat"] + random.uniform(-0.003, 0.003)
                lon = ref_node["lon"] + random.uniform(-0.003, 0.003)
            else:
                lat = BASE_LAT + random.uniform(-0.01, 0.01)
                lon = BASE_LON + random.uniform(-0.01, 0.01)

            incidents.append({
                "incident_id": f"INC{str(incident_id).zfill(3)}",
                "zone_id": zone_id,
                "type": crime_type,
                "severity": severity,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M"),
                "lat": round(lat, 4),
                "lon": round(lon, 4),
            })
            incident_id += 1

    return incidents


def generate_zone_attributes():
    zones = {}
    for zone_id, profile in ZONE_PROFILES.items():
        zones[zone_id] = {
            "lighting_score": profile["lighting"],
            "crowd_density_day": profile["crowd_day"],
            "crowd_density_night": profile["crowd_night"],
            "isolation_index": profile["isolation"],
            "emergency_facility_within_500m": profile["emergency"],
            "transit_accessibility": profile["transit"],
        }
    return zones


def generate_emergency_facilities():
    facilities = [
        {"facility_id": "F001", "type": "police_station", "lat": 28.612, "lon": 77.208, "name": "CP Police Station", "operational_24h": True},
        {"facility_id": "F002", "type": "hospital", "lat": 28.616, "lon": 77.213, "name": "Ram Manohar Lohia Hospital", "operational_24h": True},
        {"facility_id": "F003", "type": "police_station", "lat": 28.622, "lon": 77.219, "name": "Parliament Street Police", "operational_24h": True},
        {"facility_id": "F004", "type": "hospital", "lat": 28.628, "lon": 77.216, "name": "Dr. RML Hospital", "operational_24h": True},
        {"facility_id": "F005", "type": "emergency_helpdesk", "lat": 28.630, "lon": 77.219, "name": "Rajiv Chowk Help Desk", "operational_24h": False},
        {"facility_id": "F006", "type": "police_station", "lat": 28.611, "lon": 77.230, "name": "ITO Police Post", "operational_24h": False},
        {"facility_id": "F007", "type": "hospital", "lat": 28.614, "lon": 77.227, "name": "Lok Nayak Hospital", "operational_24h": True},
        {"facility_id": "F008", "type": "emergency_helpdesk", "lat": 28.624, "lon": 77.211, "name": "Shivaji Stadium Kiosk", "operational_24h": True},
    ]
    return facilities


def save_all(data_dir):
    os.makedirs(data_dir, exist_ok=True)

    road_segments = {"nodes": NODES, "edges": EDGES}
    with open(os.path.join(data_dir, "road_segments.json"), "w") as f:
        json.dump(road_segments, f, indent=2)

    zones = generate_zone_attributes()
    with open(os.path.join(data_dir, "zone_attributes.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "zone_id", "lighting_score", "crowd_density_day", "crowd_density_night",
            "isolation_index", "emergency_facility_within_500m", "transit_accessibility",
        ])
        writer.writeheader()
        for zone_id, attrs in zones.items():
            writer.writerow({"zone_id": zone_id, **attrs})

    incidents = generate_realistic_incidents()
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

    print(f"Generated realistic data for Connaught Place, New Delhi:")
    print(f"  Nodes: {len(NODES)}")
    print(f"  Edges: {len(EDGES)}")
    print(f"  Zones: {len(zones)}")
    print(f"  Crime incidents: {len(incidents)}")
    print(f"  Emergency facilities: {len(facilities)}")
    print(f"\nZone profiles:")
    for zone_id, profile in ZONE_PROFILES.items():
        print(f"  {zone_id}: {profile['name']} ({profile['type']})")


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "..", "app", "data")
    save_all(data_dir)
