from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "automation_hub_sites.json"


@dataclass(frozen=True, slots=True)
class WordPressSite:
    site_id: str
    name: str
    url: str
    secret_name: str
    language: str
    content_type: str
    group: str
    persona: str
    tone: str
    theme: str
    target_chars: int
    image_min: int
    image_max: int


def load_wordpress_sites(path: Path = REGISTRY_PATH) -> list[WordPressSite]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sites: list[WordPressSite] = []
    for row in raw.get("sites", []):
        if row.get("platform") != "wordpress":
            continue
        sites.append(WordPressSite(
            site_id=row["site_id"],
            name=row["name"],
            url=row["url"].rstrip("/"),
            secret_name=row.get("secret_name", ""),
            language=row.get("language", "en"),
            content_type=row.get("content_type", "blog"),
            group=row.get("group", ""),
            persona=row.get("persona", "Specialist editorial desk"),
            tone=row.get("tone", "Clear, practical and source-aware"),
            theme=(row.get("keyword_rules") or {}).get("theme", row["name"]),
            target_chars=int(row.get("target_chars", 2400)),
            image_min=max(0, int(row.get("image_min", 0))),
            image_max=min(2, max(0, int(row.get("image_max", 2)))),
        ))
    if len(sites) != 27:
        raise RuntimeError(f"WordPress registry must contain exactly 27 sites; found {len(sites)}")
    if len({site.site_id for site in sites}) != 27 or len({site.url for site in sites}) != 27:
        raise RuntimeError("WordPress registry contains duplicate site_id or URL")
    return sites


def site_map() -> dict[str, WordPressSite]:
    return {site.site_id: site for site in load_wordpress_sites()}

