# Nirbhaya SafeTrack - Time Context Module


TIME_PERIODS = {
    (5, 8): {"label": "dawn", "crime": 0.5, "isolation": 0.4},
    (8, 18): {"label": "daytime", "crime": 0.6, "isolation": 0.3},
    (18, 21): {"label": "evening", "crime": 0.8, "isolation": 0.7},
    (21, 24): {"label": "night", "crime": 1.0, "isolation": 1.0},
    (0, 5): {"label": "late_night", "crime": 1.2, "isolation": 1.3},
}


def get_time_multiplier(hour):
    hour = int(hour) % 24
    for (start, end), multipliers in TIME_PERIODS.items():
        if start <= hour < end:
            return {"label": multipliers["label"], "crime": multipliers["crime"], "isolation": multipliers["isolation"]}
    return {"label": "night", "crime": 1.0, "isolation": 1.0}


def get_all_time_periods():
    return [
        {"hour": h, **get_time_multiplier(h)}
        for h in range(24)
    ]
