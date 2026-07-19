#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_tsj_gp_elements.py
theseouljournal.com의 GP Elements를 조사해서
{{post_title}} 등 미치환 템플릿 태그가 어디서 오는지 특정.
"""
import os, requests

SITE = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["THESEOULJOURNALCOM"]
auth = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

r = requests.get(f"{SITE}/wp-json/wp/v2/gp_elements", auth=auth,
                  params={"per_page": 50, "context": "edit",
                           "_fields": "id,title,status,content,meta"}, timeout=20)
log(f"HTTP {r.status_code}")
data = r.json() if r.status_code == 200 else []
log(f"gp_elements 개수: {len(data)}")

for el in data:
    title = (el.get("title", {}) or {}).get("rendered") or (el.get("title", {}) or {}).get("raw", "")
    content = (el.get("content", {}) or {}).get("raw") or (el.get("content", {}) or {}).get("rendered", "")
    meta = el.get("meta", {})
    has_ph = "post_title" in content or "author_meta" in content or "post_date" in content
    log(f"[{el['id']}] status={el.get('status')} title={title!r} type={meta.get('_generate_element_type')} "
        f"hook={meta.get('_generate_hook')} display={meta.get('_generate_element_display')} has_placeholder={has_ph}")
    if has_ph:
        log("  >>> CONTENT (raw):")
        log(content[:1500])
        log("  >>> META:")
        log(str(meta)[:800])

with open("inspect_tsj_gp_elements_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
