from __future__ import annotations

import json

from control_center.orchestrator import generate_text


PROMPT = 'Return exactly this JSON object and nothing else: {"orchestrator_smoke_test":"ok"}'


def main() -> None:
    text, meta = generate_text(PROMPT, task_type="wordpress")
    print(json.dumps({"provider": meta["provider"], "model": meta["model"], "response": text[:500]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
