# Nirbhaya SafeTrack

> Intelligent safe route planner with temporal-contextual safety scoring and explainable AI routing.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.0-lightgrey.svg)

## 🌐 Live Demo
https://web-production-e1a63.up.railway.app
---

## The Problem

Every day, millions of people navigate cities without knowing which routes are actually safe. Existing "safe route" apps overlay static crime density on a map and find the shortest path with a penalty. **That's not intelligent.** The same street at 3pm vs 11pm has a completely different safety profile — and traditional systems can't explain why.

## What Makes This Different

- **Temporal-Contextual Scoring**: Edge weights are a function of time, user context, and multi-factor fusion. Safety scores change by hour of day. Dawn ≠ Night ≠ Late Night.
- **Explainable Routing**: After Dijkstra runs, the system explains *why* a route was chosen in plain English with factor contribution breakdowns. Not a black box.
- **Personalizable Weights**: Users tune their own safety priorities via sliders — "I care more about lighting than crime stats" — and routes update in real time.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Browser)                     │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────┐  │
│  │ Searchable  │ │   Leaflet    │ │  Explanation Panel    │  │
│  │ Dropdowns   │ │  Dark Map    │ │  + Factor Bars        │  │
│  └──────┬──────┘ └──────┬───────┘ └───────────┬───────────┘  │
│         │               │                      │              │
│  ┌──────┴───────────────┴──────────────────────┴───────────┐ │
│  │              Route Comparison Cards                     │ │
│  └────────────────────────┬────────────────────────────────┘ │
└───────────────────────────┼─────────────────────────────────┘
                            │ REST API (JSON)
┌───────────────────────────┼─────────────────────────────────┐
│                     Backend (Flask)                         │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────┐ │
│  │  Route API  │ │ Safety API   │ │   Explain API         │ │
│  │ /compute    │ │ /score       │ │   /route              │ │
│  │ /compare    │ │ /heatmap     │ │                       │ │
│  └──────┬──────┘ └──────┬───────┘ └───────────┬───────────┘ │
│         │               │                      │              │
│  ┌──────┴───────────────┴──────────────────────┴───────────┐ │
│  │              Engine Layer                               │ │
│  │  ┌────────────┐ ┌─────────────┐ ┌────────────────────┐  │ │
│  │  │ Dijkstra   │ │  Safety     │ │   Explainer        │  │ │
│  │  │ Runner     │ │  Scorer     │ │   (NLG)            │  │ │
│  │  └────────────┘ └─────────────┘ └────────────────────┘  │ │
│  │  ┌─────────────────────────────────────────────────┐    │ │
│  │  │           Graph Builder (NetworkX)              │    │ │
│  │  └─────────────────────────────────────────────────┘    │ │
│  └────────────────────────┬────────────────────────────────┘ │
│                           │                                   │
│  ┌────────────────────────┴────────────────────────────────┐ │
│  │                    Data Layer                           │ │
│  │  road_segments.json │ crime_incidents.csv │ zones.csv   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## How the Scoring Works

The edge weight for graph traversal is computed as:

```python
edge_weight = distance_m × (1 + k × safety_penalty)

where k = 0 (fastest), 2 (balanced), or 5 (safest)
```

The safety penalty is a weighted composite of 6 factors:

| Factor | Default Weight | What It Measures |
|---|---|---|
| **Crime Risk** | 30% | Historical incident density, exponentially decayed by recency |
| **Street Lighting** | 20% | Presence and coverage of street lights |
| **Area Isolation** | 20% | How isolated the area is (time-adjusted) |
| **Foot Traffic** | 10% | Day/night crowd density |
| **Emergency Access** | 10% | Proximity to police stations, hospitals |
| **Transit Access** | 10% | Public transport availability |

### Time-of-Day Multipliers

| Period | Hours | Crime Multiplier | Isolation Multiplier |
|---|---|---|---|
| Late Night | 00–05 | 1.2× | 1.3× |
| Dawn | 05–08 | 0.5× | 0.4× |
| Daytime | 08–18 | 0.6× | 0.3× |
| Evening | 18–21 | 0.8× | 0.7× |
| Night | 21–24 | 1.0× | 1.0× |

### Incident Recency Decay

```python
recency_weight = exp(-0.005 × hours_since_incident)
# Half-life: ~140 hours (~6 days)
```

## Setup

```bash
# Clone and create virtual environment
git clone <repo-url>
cd nirbhaya-safetrack
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
flask --app app run --debug
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## API Endpoints

| Method | Endpoint | Description | Example |
|---|---|---|---|
| `POST` | `/api/route/compute` | Compute routes with mode, time, preferences | See below |
| `POST` | `/api/route/compare` | Compare all three routing modes | `{origin, destination}` |
| `GET` | `/api/safety/score` | Get safety score for a zone | `?zone_id=Z012&hour=22` |
| `GET` | `/api/safety/heatmap` | Get zone scores for heatmap overlay | `?hour=22` |
| `GET` | `/api/nodes` | List all graph nodes with names | — |
| `GET` | `/api/health` | Health check with graph stats | — |

### Route Compute Request

```json
POST /api/route/compute
{
  "origin": "N001",
  "destination": "N010",
  "departure_time": "22:00",
  "mode": "all",
  "user_preferences": {
    "crime": 0.30,
    "lighting": 0.20,
    "isolation": 0.20,
    "crowd": 0.10,
    "emergency": 0.10,
    "transit": 0.10
  }
}
```

### Route Compute Response

```json
{
  "safest": {
    "path": ["N001", "N008", "N009", "N010"],
    "coordinates": [
      {"node_id": "N001", "lat": 28.6139, "lon": 77.209, "name": "Connaught Place Junction"},
      ...
    ],
    "distance_m": 1250,
    "safety_score": 0.15,
    "explanation": "This safest route is rated very safe (high confidence) for nighttime when many areas become significantly less safe. It prioritizes well-lit streets and fewer reported incidents.",
    "summary": {
      "mode": "Safest",
      "path_names": ["Connaught Place Junction", "Tolstoy Marg", ...],
      "estimated_walk_time_min": 15.6
    }
  },
  "fastest": { ... },
  "balanced": { ... }
}
```

## Running Tests

```bash
pytest tests/ -v
```

22 tests covering:
- Safety scorer bounds and time multipliers
- Dijkstra pathfinding for all modes
- Explanation generation quality

## Deployment

### Railway

```bash
# Push to GitHub
git push origin main

# Connect to Railway
# Add environment variable: FLASK_ENV=production
# Railway auto-detects Procfile and deploys
```

The `Procfile` is pre-configured for gunicorn with 2 workers. The graph loads as a singleton on startup.

## Built With

[![Flask](https://img.shields.io/badge/Flask-3.0-000.svg)](https://flask.palletsprojects.com/)
[![NetworkX](https://img.shields.io/badge/NetworkX-3.2-2d6a4f.svg)](https://networkx.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900.svg)](https://leafletjs.com/)
[![CARTO](https://img.shields.io/badge/CARTO-Dark--Theme-eb154e.svg)](https://carto.com/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.x-ff6384.svg)](https://www.chartjs.org/)

## Social Impact

In India, over 30,000 crimes against women are reported annually (NCRB 2022). The actual number is likely much higher due to underreporting. SafeTrack isn't just a technical project — it's a tool that could genuinely help people make informed decisions about their safety while navigating cities.

Every route computed is a potential safer journey home.

## Future Work

| Feature | Description | Impact |
|---|---|---|
| **ML Time Multipliers** | Replace hand-crafted multipliers with Random Forest trained on historical incident timestamps | More accurate, adaptive scoring |
| **User Feedback Loop** | "Felt unsafe" markings create soft penalty boosts via collaborative filtering | Community-driven safety data |
| **Semantic NLG** | Replace template explanations with sentence-transformers for varied natural language | More human-like explanations |
| **DBSCAN Clustering** | Detect spatial crime hotspots instead of pre-defined zones | City-agnostic deployment |
| **OSMnx Integration** | Pull real road networks from OpenStreetMap for any city | No synthetic data needed |
| **SQLite Persistence** | Store user preferences, route history, and feedback | Personalized experience over time |
| **Mobile App** | React Native wrapper with offline map caching | Real-world usability |
| **Real-time Data** | Integrate live CCTV density, event calendars, weather | Dynamic safety adjustments |

## License

MIT — Build on it, improve it, ship it.
