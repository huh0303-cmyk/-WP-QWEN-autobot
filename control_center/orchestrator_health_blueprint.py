from __future__ import annotations

from flask import Blueprint, jsonify

from .orchestrator import provider_health


orchestrator_blueprint = Blueprint("orchestrator", __name__)


@orchestrator_blueprint.get("/api/orchestrator/health")
def health():
    return jsonify(providers=provider_health())
