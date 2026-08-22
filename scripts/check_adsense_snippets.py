#!/usr/bin/env python3
"""k-health365.com에 활성화된 Code Snippets 중 AdSense 관련된 것들을 나열해서
중복 삽입 원인을 찾는다. 읽기 전용."""
import os
import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("KHEALTH365COM", "").strip()


def main():
    if not PW:
        raise SystemExit("Missing KHEALTH365COM secret")
    r = requests.get(f"{SITE}/wp-json/code-snippets/v1/snippets", auth=(USER, PW),
                      params={"per_page": 100}, timeout=45)
    r.raise_for_status()
    snippets = r.json()
    snippets = snippets if isinstance(snippets, list) else snippets.get("data", snippets.get("items", []))
    print(f"전체 스니펫 {len(snippets)}개")
    for s in snippets:
        code = s.get("code", "")
        active = s.get("active")
        if "adsbygoogle" in code.lower() or "adsense" in s.get("name", "").lower() or "ca-pub" in code:
            print(f"\n--- id={s['id']} name={s['name']!r} active={active} ---")
            print(code[:400])


if __name__ == "__main__":
    main()
