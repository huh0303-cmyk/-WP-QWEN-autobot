from __future__ import annotations

import argparse
import json

from .registry import SiteRegistry
from .sheet_schema import SITE_SETTINGS_HEADER


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified content automation control plane")
    parser.add_argument("command", choices=["validate", "summary", "sheet-json"])
    parser.add_argument("--registry", default=None)
    args = parser.parse_args()

    registry = SiteRegistry.load(args.registry) if args.registry else SiteRegistry.load()
    if args.command == "validate":
        problems = registry.validate()
        print(json.dumps(problems, ensure_ascii=False, indent=2))
        return 1 if problems else 0
    if args.command == "summary":
        print(json.dumps(registry.summary(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "sheet-json":
        payload = {"header": SITE_SETTINGS_HEADER, "rows": [site.to_sheet_row() for site in registry.sites]}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
