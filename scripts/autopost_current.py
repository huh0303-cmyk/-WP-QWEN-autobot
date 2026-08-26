#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current WordPress publisher entrypoint controlled by Google Sheets.

Keeps the mature autopost_mega engine while applying current operational metadata that
must not regress to legacy labels retained in the large historical module.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import autopost_mega as base

from automation_hub.wordpress_adapter import apply_wordpress_registry

# kskin365.com was restored to the active 25-blog network. The legacy module still carried
# a stale 'Retired Site' author label, which must never reach newly published content.
kskin_author = {
    "name": "Korean Skincare Editorial Desk",
    "email": "editor@kskin365.com",
    "slug": "kskin365-com-desk",
    "bio": (
        "Korean Skincare Editorial Desk. Source-checked ingredient, routine and skin-safety "
        "guidance within this site's editorial scope."
    ),
}
base.AUTHOR_BY_SITE_DEF["kskin365.com"] = kskin_author
base.AUTHOR_BY_SITE["kskin365.com"] = kskin_author


def load_dashboard_settings() -> None:
    source = os.getenv("AUTOMATION_HUB_SOURCE", "github").strip().lower()
    if source == "github":
        from automation_hub.registry import SiteRegistry

        registry = SiteRegistry.load()
    elif source == "sheets":
        from load_automation_hub_from_sheets import load_runtime_registry

        registry = load_runtime_registry()
    else:
        raise RuntimeError(f"unsupported AUTOMATION_HUB_SOURCE: {source}")

    sites, personas = apply_wordpress_registry(base.SITES_CONFIG, base.SITE_PERSONA, registry)
    base.SITES_CONFIG = sites
    base.SITE_PERSONA = personas
    print(f"🎛️ Automation Hub 설정 적용: WordPress {len(sites)}개 / source={source}")

if __name__ == "__main__":
    load_dashboard_settings()
    base.main()
