#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import requests

from replicate_image_provider import generate_image_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("--theme", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    url = generate_image_url(args.subject, theme=args.theme)
    if not url:
        raise SystemExit("approved image providers returned no image")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    output.write_bytes(response.content)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
