Production integration target:
- import generate_article from control_center.generator_orchestrated OR replace control_center.generator with the orchestrated implementation.
- install control_center.orchestrator_routes.install(app) during Flask app setup.
- deploy only after tests and draft-only failover acceptance test.
