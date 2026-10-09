#!/usr/bin/env python3
"""Read-only health probe: every writer engine and image source, no secrets printed.
Exit 0 always (it is a report); the summary lists which engines are usable right now."""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import requests
import economy_text as e
import blogger_free_image as img

rows = []
def add(kind, name, ok, note=""):
    rows.append({"kind": kind, "name": name, "ok": bool(ok), "note": str(note)[:160]})
    print(("OK  " if ok else "FAIL"), kind, name, note if not ok else "")

keys = e._gemini_keys()
for n in e._KEY_NAMES:
    v = os.getenv(n, "").strip()
    if not v:
        add("gemini-key", n, False, "not set")
    elif len(v) < 20:
        add("gemini-key", n, False, f"invalid placeholder (len {len(v)})")
for kid, key in keys:
    for model in e.FREE_GEMINI_MODELS:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                              headers={"x-goog-api-key": key},
                              json={"contents": [{"parts": [{"text": "Reply with the single word OK"}]}],
                                    "generationConfig": {"maxOutputTokens": 20}}, timeout=60)
            msg = ""
            if not r.ok:
                try: msg = r.json().get("error", {}).get("message", "")[:100]
                except ValueError: msg = r.text[:100]
            add("gemini", f"{kid}/{model}", r.ok, f"HTTP {r.status_code} {msg}")
        except requests.RequestException as ex:
            add("gemini", f"{kid}/{model}", False, type(ex).__name__)

for spec in e.OPENAI_COMPAT:
    provider, key_env, url, _env, _d = spec
    key = os.getenv(key_env, "").strip()
    if not key:
        add(provider, "key", False, "not set"); continue
    for model in e._compat_models(spec):
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                              json={"model": model, "max_tokens": 200, "messages": [{"role": "user", "content": "Reply OK"}]}, timeout=60)
            msg = ""
            if not r.ok:
                try: msg = str(r.json().get("error", {}).get("message", ""))[:100]
                except ValueError: msg = r.text[:100]
            add(provider, model, r.ok, f"HTTP {r.status_code} {msg}")
        except requests.RequestException as ex:
            add(provider, model, False, type(ex).__name__)

for q in ("Seoul palace autumn", "Korean skincare routine", "jeju island coast"):
    for fn in (img._pexels, img._pixabay, img._wikimedia):
        try:
            f = fn(q)
            add("image", f"{fn.__name__} '{q}'", f, "no match" if not f else "")
        except Exception as ex:
            add("image", f"{fn.__name__} '{q}'", False, type(ex).__name__)

json.dump(rows, open("writer_image_health.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok_w = [r for r in rows if r["kind"] in ("gemini", "groq", "openrouter", "cerebras") and r["ok"]]
print("\nUSABLE WRITERS:", sorted({r["kind"] for r in ok_w}), len(ok_w), "model/key combos")
print("USABLE IMAGE SOURCES:", sorted({r["name"].split()[0] for r in rows if r["kind"] == "image" and r["ok"]}))
