from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import SiteConfig


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "automation_hub_sites.json"


class SiteRegistry:
    def __init__(self, sites: Iterable[SiteConfig]):
        self.sites = list(sites)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_REGISTRY_PATH) -> "SiteRegistry":
        registry_path = Path(path)
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        records = raw.get("sites", raw) if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ValueError("registry must be a list or an object containing sites")
        return cls(SiteConfig.from_dict(record) for record in records)

    @classmethod
    def from_sheet_rows(cls, header: list[str], rows: list[list[object]]) -> "SiteRegistry":
        sites = [SiteConfig.from_sheet_row(header, row) for row in rows if row and str(row[0]).strip()]
        return cls(sites)

    def validate(self) -> dict[str, list[str]]:
        problems: dict[str, list[str]] = {}
        seen_ids: set[str] = set()
        seen_destinations: set[tuple[str, str]] = set()
        for site in self.sites:
            errors = site.validate()
            if site.site_id in seen_ids:
                errors.append("duplicate site_id")
            seen_ids.add(site.site_id)
            destination = (site.platform, site.url.rstrip("/").lower())
            if destination in seen_destinations:
                errors.append("duplicate platform destination")
            seen_destinations.add(destination)
            if errors:
                problems[site.site_id or f"row-{len(seen_ids)}"] = errors
        return problems

    def enabled(self, platform: str | None = None) -> list[SiteConfig]:
        return [
            site for site in self.sites
            if site.enabled and (platform is None or site.platform == platform)
        ]

    def by_id(self, site_id: str) -> SiteConfig:
        for site in self.sites:
            if site.site_id == site_id:
                return site
        raise KeyError(site_id)

    def summary(self) -> dict[str, int]:
        result = {"total": len(self.sites), "enabled": len(self.enabled())}
        for site in self.sites:
            result[site.platform] = result.get(site.platform, 0) + 1
            result[site.content_type] = result.get(site.content_type, 0) + 1
        return result
