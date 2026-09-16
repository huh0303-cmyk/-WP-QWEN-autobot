from __future__ import annotations

import json
import os

from control_center.orchestrator import provider_health


def main() -> None:
    configured = {
        "openai": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()),
        "gemini": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
    }
    print(json.dumps({"configured": configured, "health": provider_health()}, ensure_ascii=False, indent=2))
    if not configured["anthropic"]:
        raise SystemExit("ANTHROPIC_API_KEY is not configured; Claude failover is not deployable yet")


if __name__ == "__main__":
    main()
