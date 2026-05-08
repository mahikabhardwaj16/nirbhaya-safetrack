# Nirbhaya SafeTrack - Flask Application Factory

import os
import threading
from flask import Flask, render_template, jsonify
from flask_cors import CORS

from .data import load_datasets
from .engine.graph_builder import build_graph
from .engine.community_feedback import init_feedback

_graph = None
_datasets = None
_graph_lock = threading.Lock()


def get_graph():
    global _graph, _datasets
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                pass
    return _graph


def get_datasets():
    global _datasets
    return _datasets


def _initialize_graph(app):
    global _graph, _datasets
    data_dir = app.config.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
    _datasets = load_datasets(data_dir)
    _graph = build_graph(_datasets)
    app.config["graph"] = _graph
    app.config["datasets"] = _datasets
    init_feedback()
    app.logger.info(f"Graph loaded: {_graph.number_of_nodes()} nodes, {_graph.number_of_edges()} edges")


def create_app(config_override=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    CORS(app)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    app.config["DATA_DIR"] = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

    if config_override:
        app.config.update(config_override)

    _initialize_graph(app)

    from .routes.route_api import route_api
    from .routes.safety_api import safety_api
    from .routes.explain_api import explain_api
    from .routes.feedback_api import feedback_api

    app.register_blueprint(route_api)
    app.register_blueprint(safety_api)
    app.register_blueprint(explain_api)
    app.register_blueprint(feedback_api)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        from .engine.community_feedback import get_feedback_stats
        fb_stats = get_feedback_stats()
        return jsonify({
            "status": "ok",
            "graph_nodes": _graph.number_of_nodes() if _graph else 0,
            "graph_edges": _graph.number_of_edges() if _graph else 0,
            "zones_loaded": len(_datasets["zone_attributes"]) if _datasets else 0,
            "community_feedback_active": True,
            "community_reports": fb_stats.get("total_reports", 0),
        })

    @app.route("/api/nodes")
    def get_nodes():
        if not _graph:
            return jsonify({"error": "Graph not loaded"}), 500
        nodes = []
        for node_id, data in _graph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "name": data.get("name", node_id),
                "zone_id": data.get("zone_id"),
            })
        return jsonify({"nodes": nodes})

    return app
