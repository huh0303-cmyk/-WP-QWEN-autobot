#!/usr/bin/env python3
"""Create article-specific JobKorea365 product matches. This script never writes to WordPress."""
from __future__ import annotations
import json, re, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
inventory = json.loads((ROOT / "reports/jobkorea365-coupang-post-inventory-2026-10-31.json").read_text(encoding="utf-8"))
catalog = json.loads((ROOT / "data/affiliate/jobkorea365-products.json").read_text(encoding="utf-8"))
products = catalog["products"]
by_id = {p["id"]: p for p in products}
usage = {p["id"]: 0 for p in products}

RX = {
    "worksite": re.compile(r"\b(manufactur|factory|industrial|construction|warehouse|logistics|e-9|fisheries|agricultur|slaughterhouse|plant placement|factory floor|production)\b", re.I),
    "housing": re.compile(r"\b(dormitory|housing|accommodation|relocation|residential|worker housing)\b", re.I),
    "professional": re.compile(r"\b(high-skilled|foreign professionals|professional|tech worker|it worker|startup|remote jobs|remote work|hr jobs|law firm)\b", re.I),
    "study": re.compile(r"\b(topik|eps-topik|korean language|english teaching|language study|office slang|workplace conversation|vocabulary)\b", re.I),
    "interview": re.compile(r"\b(resume|cv|interview|job application|recruitment|job seeker|career|first job|job listings|hr jobs)\b", re.I),
    "paperwork": re.compile(r"\b(visa|work permit|passport|certificate|contract|payroll|salary|wage|insurance|deduction|labor|employment|eligibility|regulation|compliance|rights|compensation|legal)\b", re.I),
    "seasonal": re.compile(r"\b(e-8|seasonal worker|fisheries)\b", re.I),
}

TOPIC = {
    "worksite": ["jk11","jk12","jk15","jk16","jk13","jk14","jk17","jk18","jk19","jk02","jk04","jk48"],
    "seasonal": ["jk17","jk18","jk19","jk24","jk04","jk48","jk49"],
    "housing": ["jk21","jk22","jk23","jk25","jk26","jk27","jk29"],
    "study": ["jk01","jk02","jk41","jk42","jk43","jk44","jk45","jk33","jk47"],
    "interview": ["jk03","jk04","jk05","jk06","jk07","jk08","jk09","jk10"],
    "professional": ["jk08","jk09","jk10","jk38","jk30","jk04","jk48"],
    "paperwork": ["jk04","jk05","jk37","jk48","jk49","jk43"],
    "general": ["jk03","jk04","jk48","jk49","jk01","jk43"],
}
ESSENTIAL = {
    "worksite": ["jk18","jk19","jk24","jk46","jk30","jk28","jk17"],
    "seasonal": ["jk19","jk24","jk28","jk46","jk17","jk30"],
    "housing": ["jk21","jk22","jk23","jk25","jk26","jk27","jk29"],
    "study": ["jk30","jk46","jk08","jk28","jk19"],
    "interview": ["jk08","jk30","jk46","jk28","jk40"],
    "professional": ["jk30","jk46","jk08","jk28","jk40"],
    "paperwork": ["jk46","jk30","jk49","jk40","jk48"],
    "general": ["jk46","jk30","jk40","jk49","jk48"],
}
PREMIUM = {
    "worksite": ["jk40","jk31","jk33","jk36"],
    "seasonal": ["jk40","jk31","jk33"],
    "housing": ["jk40","jk31","jk33"],
    "study": ["jk33","jk31","jk35","jk40"],
    "interview": ["jk31","jk10","jk09","jk32"],
    "professional": ["jk31","jk32","jk34","jk35","jk36","jk39"],
    "paperwork": ["jk05","jk37","jk31","jk33"],
    "general": ["jk40","jk31","jk05"],
}

def rank(pid, post_id, text):
    p = by_id[pid]
    hits = [kw for kw in p["keywords"] if kw.lower() in text]
    score = sum(min(5, max(1, len(kw)//5)) for kw in hits)
    return (-score, usage[pid], hashlib.sha256(f"{post_id}:{pid}".encode()).hexdigest())

def pick(ids, count, post_id, text, used):
    eligible = [pid for pid in ids if pid in by_id and pid not in used]
    eligible.sort(key=lambda pid: rank(pid, post_id, text))
    chosen = eligible[:count]
    for pid in chosen:
        used.add(pid)
        usage[pid] += 1
    return chosen

results = []
for post in inventory["posts"]:
    title = post.get("title", "")
    text = " ".join([title, post.get("excerpt", "")]).lower()
    flags = {k: bool(rx.search(title)) for k,rx in RX.items()}

    # Prioritize specific contexts; do not place industrial PPE in general visa/salary explainers.
    if flags["worksite"]:
        topic_ids = TOPIC["worksite"] + (TOPIC["paperwork"] if flags["paperwork"] else [])
        daily_key = "worksite"
        premium_key = "worksite"
    elif flags["seasonal"]:
        topic_ids = TOPIC["seasonal"] + (TOPIC["paperwork"] if flags["paperwork"] else [])
        daily_key = "seasonal"
        premium_key = "seasonal"
    elif flags["housing"]:
        topic_ids = TOPIC["housing"]
        daily_key = "housing"
        premium_key = "housing"
    elif flags["study"]:
        topic_ids = TOPIC["study"] + (TOPIC["paperwork"] if flags["paperwork"] else [])
        daily_key = "study"
        premium_key = "study"
    elif flags["interview"]:
        topic_ids = TOPIC["interview"] + (TOPIC["paperwork"] if flags["paperwork"] else [])
        daily_key = "interview"
        premium_key = "interview"
    elif flags["professional"]:
        topic_ids = TOPIC["professional"] + (TOPIC["paperwork"] if flags["paperwork"] else [])
        daily_key = "professional"
        premium_key = "professional"
    elif flags["paperwork"]:
        topic_ids = TOPIC["paperwork"]
        daily_key = "paperwork"
        premium_key = "paperwork"
    else:
        topic_ids = TOPIC["general"]
        daily_key = "general"
        premium_key = "general"

    used = set()
    topic_count = 3 if (flags["worksite"] or flags["housing"] or flags["study"] or flags["interview"] or flags["professional"]) else 2
    chosen = pick(topic_ids, topic_count, post["id"], text, used)
    chosen += pick(ESSENTIAL[daily_key], 2, post["id"], text, used)
    chosen += pick(PREMIUM[premium_key], 1, post["id"], text, used)

    # For strong purchase-intent topics, add one more matched item if a unique candidate exists.
    if topic_count == 3 and len(chosen) < 7:
        extra_ids = topic_ids + ESSENTIAL[daily_key] + PREMIUM[premium_key]
        chosen += pick(extra_ids, 1, post["id"], text, used)

    # Fill to six only with context-safe options; never force PPE into a non-worksite post.
    if len(chosen) < 6:
        safe = TOPIC[daily_key] if daily_key in TOPIC else TOPIC["general"]
        chosen += pick(safe + ESSENTIAL[daily_key] + PREMIUM[premium_key], 6-len(chosen), post["id"], text, used)

    items = []
    for pid in chosen[:7]:
        p = by_id[pid]
        hits = [kw for kw in p["keywords"] if kw.lower() in text]
        items.append({
            "product_id": pid, "english_name": p["name"], "group": p["group"],
            "price_tier": p["price_tier"], "matched_keywords": hits[:8],
            "affiliate_url_status": "pending_portal_generated_link",
            "official_image_status": "pending_portal_creative"
        })
    results.append({
        "post_id": post["id"], "title": title, "url": post["url"],
        "product_count": len(items), "products": items, "status": "planned_not_inserted"
    })

out = {
    "site": inventory["site"], "generated_date": inventory["generated_at"],
    "mode": "matching_manifest_only_no_writes", "posts_total": len(results),
    "target_per_post": "5-10", "product_pool_size": len(products),
    "unique_products_used": len({x["product_id"] for row in results for x in row["products"]}),
    "placement_counts": usage, "posts": results
}
path = ROOT / "reports/jobkorea365-coupang-post-product-mapping-2026-10-31.json"
path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("mode","posts_total","target_per_post","product_pool_size","unique_products_used")}, ensure_ascii=False))
print("COUNT_RANGE", min(x["product_count"] for x in results), max(x["product_count"] for x in results))
