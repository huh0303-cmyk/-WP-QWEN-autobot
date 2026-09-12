#!/usr/bin/env python3
"""Perceptual-hash pass: the exact-URL dedup check found zero repeats, but the
user spotted the same passport stock photo on multiple articles -> it must be
the same underlying stock photo re-selected under a different uploaded
filename each time. Download every recent image, compute an 8x8 average hash,
and group by near-identical hash (Hamming distance <= 4) regardless of URL."""
import json
import os
import socket
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image
import io

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only


def ahash(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((8, 8), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    return int(bits, 2)


def hamming(a, b):
    return bin(a ^ b).count("1")


def fetch_and_hash(entry):
    try:
        r = requests.get(entry["image_url"], timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
            return None
        h = ahash(r.content)
        return {**entry, "hash": h}
    except Exception:
        return None


def main():
    rows = json.loads(open("artifacts/duplicate-images-raw.json", encoding="utf-8").read())
    print(f"hashing {len(rows)} images...")
    hashed = []
    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = [pool.submit(fetch_and_hash, r) for r in rows]
        for i, future in enumerate(as_completed(futures)):
            res = future.result()
            if res:
                hashed.append(res)
            if (i + 1) % 20 == 0:
                print(f"  hashed {i+1}/{len(rows)}")

    print(f"successfully hashed {len(hashed)}/{len(rows)}")

    groups = []
    used = set()
    for i, a in enumerate(hashed):
        if i in used:
            continue
        group = [a]
        for j, b in enumerate(hashed[i + 1:], start=i + 1):
            if j in used:
                continue
            if hamming(a["hash"], b["hash"]) <= 4:
                group.append(b)
                used.add(j)
        if len(group) > 1:
            groups.append(group)
            used.add(i)

    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/duplicate-images-phash-groups.json", "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nfound {len(groups)} near-duplicate groups (Hamming <= 4):")
    for g in sorted(groups, key=lambda x: -len(x)):
        sites = sorted(set(e["site"] for e in g))
        print(f"\n[{len(g)}x across {len(sites)} sites]")
        for e in g:
            print(f"   {e['site']} #{e['post_id']} ({e['date'][:10]}): {e['title']}")
            print(f"      {e['image_url']}")


if __name__ == "__main__":
    main()
