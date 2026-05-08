# Nirbhaya SafeTrack - Community Feedback Engine

import random
import threading
from datetime import datetime, timedelta

FEEDBACK_TYPES = [
    "lighting",
    "visibility",
    "emergency_access",
    "crowd_safety",
    "incident_report",
]

FEEDBACK_TEMPLATES = {
    "lighting": [
        "Street lights non-functional in {zone}",
        "Dimly lit pathway near {zone} after 9 PM",
        "No lighting on footpath in {zone}",
        "Flickering street lamps in {zone} area",
        "Dark alley near {zone} needs better lighting",
    ],
    "visibility": [
        "Low pedestrian visibility after 10 PM in {zone}",
        "Very few people around {zone} at night",
        "Isolated stretch near {zone} feels unsafe after dark",
        "Poor visibility on walkway in {zone}",
        "No foot traffic in {zone} after 11 PM",
    ],
    "emergency_access": [
        "Limited emergency access near {zone}",
        "Nearest hospital too far from {zone}",
        "No police patrol visible in {zone} at night",
        "Emergency helpdesk not available near {zone}",
        "Difficult to find help in {zone} after midnight",
    ],
    "crowd_safety": [
        "Suspicious activity reported near {zone}",
        "Feeling unsafe in crowded area of {zone}",
        "Harassment incident near {zone} last night",
        "Groups loitering near {zone} after dark",
    ],
    "incident_report": [
        "Witnessed theft near {zone} around 11 PM",
        "Chain snatching reported near {zone}",
        "Someone was followed from {zone} last night",
        "Verbal harassment near {zone} bus stop",
    ],
}

ZONE_NAMES = {
    "Z008": "Paharganj",
    "Z010": "Connaught Place",
    "Z012": "India Gate",
    "Z013": "Mandi House",
    "Z015": "Parliament Street",
    "Z016": "Patel Chowk",
    "Z018": "Supreme Court",
    "Z019": "Jama Masjid",
    "Z020": "Delhi Gate",
    "Z021": "ITO",
    "Z022": "Khan Market",
    "Z025": "Lajpat Nagar",
}

_feedback_store = []
_store_lock = threading.Lock()
_next_id = 1

def _generate_mock_feedback():
    now = datetime.now()
    items = []
    base_time = now - timedelta(hours=48)
    for i in range(36):
        ts = base_time + timedelta(
            hours=random.randint(0, 47),
            minutes=random.randint(0, 59),
        )
        ftype = random.choice(FEEDBACK_TYPES)
        zone_id = random.choice(list(ZONE_NAMES.keys()))
        zone_name = ZONE_NAMES[zone_id]
        template = random.choice(FEEDBACK_TEMPLATES[ftype])
        message = template.format(zone=zone_name)

        severity = random.choice([1, 1, 2, 2, 3])
        items.append({
            "id": i + 1,
            "type": ftype,
            "zone_id": zone_id,
            "zone_name": zone_name,
            "message": message,
            "severity": severity,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "upvotes": random.randint(0, 24),
        })
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items

def init_feedback():
    global _next_id
    with _store_lock:
        _feedback_store[:] = _generate_mock_feedback()
        if _feedback_store:
            _next_id = max(item["id"] for item in _feedback_store) + 1

def get_recent_feedback(limit=10, since=None):
    with _store_lock:
        results = list(_feedback_store)
    if since:
        results = [r for r in results if r["timestamp"] > since]
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results[:limit]

def get_feedback_stats():
    with _store_lock:
        total = len(_feedback_store)
        if total == 0:
            return {
                "total_reports": 0,
                "top_concerns": [],
                "zone_concern_count": {},
                "by_type": {},
            }
        by_type = {}
        for item in _feedback_store:
            by_type[item["type"]] = by_type.get(item["type"], 0) + 1
        zone_counts = {}
        for item in _feedback_store:
            z = item["zone_name"]
            zone_counts[z] = zone_counts.get(z, 0) + 1
        top_zones = sorted(zone_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        concerns = []
        for item in _feedback_store[:20]:
            concerns.append({
                "zone_name": item["zone_name"],
                "type": item["type"],
                "message": item["message"],
                "severity": item["severity"],
                "upvotes": item["upvotes"],
            })
        return {
            "total_reports": total,
            "top_concerns": concerns[:5],
            "zone_concern_count": zone_counts,
            "top_zones": [{"name": z, "count": c} for z, c in top_zones],
            "by_type": by_type,
        }

def submit_feedback(feedback_type, zone_id, message, severity=1):
    global _next_id
    with _store_lock:
        item = {
            "id": _next_id,
            "type": feedback_type,
            "zone_id": zone_id,
            "zone_name": ZONE_NAMES.get(zone_id, zone_id),
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "upvotes": 0,
        }
        _next_id += 1
        _feedback_store.insert(0, item)
    return item

def get_feedback_penalty(zone_id, hour):
    with _store_lock:
        zone_feedback = [f for f in _feedback_store if f["zone_id"] == zone_id]
    if not zone_feedback:
        return 0.0
    recent_cutoff = datetime.now() - timedelta(hours=24)
    recent_count = 0
    weighted = 0.0
    for f in zone_feedback:
        try:
            ts = datetime.strptime(f["timestamp"], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            ts = datetime.now()
        hours_ago = (datetime.now() - ts).total_seconds() / 3600
        recency = max(0, 1 - hours_ago / 72)
        is_recent = ts > recent_cutoff
        type_penalty = {"lighting": 0.08, "visibility": 0.10, "emergency_access": 0.12, "crowd_safety": 0.06, "incident_report": 0.15}
        base = type_penalty.get(f["type"], 0.05)
        weighted += base * recency * f.get("severity", 1)
        if is_recent:
            recent_count += 1
    if not weighted:
        return 0.0
    penalty = min(weighted / max(len(zone_feedback), 1), 0.35)
    if hour >= 20 or hour < 6:
        penalty *= 1.5
    return round(min(penalty, 0.4), 4)
