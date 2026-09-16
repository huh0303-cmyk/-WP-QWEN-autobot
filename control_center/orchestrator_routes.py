from __future__ import annotations

from flask import jsonify

from .orchestrator import provider_health


def install(app):
    @app.get("/api/orchestrator/health")
    def orchestrator_health():
        return jsonify(providers=provider_health())
