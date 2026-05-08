# Nirbhaya SafeTrack - Data Loading Utilities

import json
import csv
import os


DATA_DIR = os.path.dirname(__file__)


def load_road_segments(filepath=None):
    filepath = filepath or os.path.join(DATA_DIR, "road_segments.json")
    with open(filepath, "r") as f:
        return json.load(f)


def load_crime_incidents(filepath=None):
    filepath = filepath or os.path.join(DATA_DIR, "crime_incidents.csv")
    incidents = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["severity"] = int(row["severity"])
            try:
                from datetime import datetime
                row["timestamp"] = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M")
            except ValueError:
                pass
            incidents.append(row)
    return incidents


def load_zone_attributes(filepath=None):
    filepath = filepath or os.path.join(DATA_DIR, "zone_attributes.csv")
    zones = {}
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zone_id = row["zone_id"]
            zones[zone_id] = {
                "lighting_score": float(row["lighting_score"]),
                "crowd_density_day": float(row["crowd_density_day"]),
                "crowd_density_night": float(row["crowd_density_night"]),
                "isolation_index": float(row["isolation_index"]),
                "emergency_facility_within_500m": row["emergency_facility_within_500m"].lower() == "true",
                "transit_accessibility": float(row["transit_accessibility"]),
            }
    return zones


def load_emergency_facilities(filepath=None):
    filepath = filepath or os.path.join(DATA_DIR, "emergency_facilities.csv")
    facilities = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["operational_24h"] = row["operational_24h"].lower() == "true"
            row["lat"] = float(row["lat"])
            row["lon"] = float(row["lon"])
            facilities.append(row)
    return facilities


def load_datasets(data_dir=None):
    if data_dir:
        global DATA_DIR
        DATA_DIR = data_dir

    return {
        "road_segments": load_road_segments(),
        "crime_incidents": load_crime_incidents(),
        "zone_attributes": load_zone_attributes(),
        "emergency_facilities": load_emergency_facilities(),
    }


def load_all_datasets(data_dir=None):
    return load_datasets(data_dir)


def get_crime_by_zone(crime_incidents):
    index = {}
    for inc in crime_incidents:
        zone_id = inc["zone_id"]
        if zone_id not in index:
            index[zone_id] = []
        index[zone_id].append(inc)
    return index
