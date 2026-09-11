"""Keep a dated, last-known-good metrics snapshot when GitHub is unavailable."""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


def valid_stamp(value):
    try:
        if not isinstance(value.get("records"), list) or not value["records"]:
            return None
        stamp = datetime.fromisoformat(value["generated_at"])
        return stamp if stamp.tzinfo is not None else None
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def best_snapshot(data_dir, remote=None):
    data_dir = Path(data_dir)
    cache = data_dir / "core_metrics_cached.json"
    candidates = [remote]
    for path in (cache, data_dir / "core_metrics_daily_latest.json", data_dir / "core_metrics_latest.json"):
        try:
            candidates.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    valid = [(valid_stamp(value), value) for value in candidates]
    valid = [(stamp, value) for stamp, value in valid if stamp is not None]
    if not valid:
        return {}
    _, best = max(valid, key=lambda item: (item[1].get("report_kind") == "daily_0700", item[0]))
    if best is remote:
        name = None
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=data_dir, delete=False) as handle:
                name = handle.name
                json.dump(best, handle, ensure_ascii=False)
            os.replace(name, cache)
        except OSError:
            pass  # A read-only disk must not prevent displaying live metrics.
        finally:
            if name and os.path.exists(name):
                os.unlink(name)
    return best
