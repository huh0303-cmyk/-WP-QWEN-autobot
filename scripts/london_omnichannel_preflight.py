from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/"config/affiliate_distribution_policy.json").read_text(encoding="utf-8-sig"))
PROFILES=json.loads((ROOT/"config/content_engine_profiles.json").read_text(encoding="utf-8-sig"))["profiles"]
YT=json.loads((ROOT/"config/youtube_channels.json").read_text(encoding="utf-8-sig"))
SNS=json.loads((ROOT/"config/sns_six_channel_policy.json").read_text(encoding="utf-8-sig"))
PROTECTED={"khealth365","krealestate365","kworld365","oliveyoung","ksa"}
CATALOGS=ROOT/"affiliate-engine"/"data"/"catalogs"
EXPECTED=POLICY["provider_allocation"]

def catalog_status(key:str)->dict:
    path=CATALOGS/f"{key}.json"
    if not path.exists(): return {"site_key":key,"status":"missing","verified_offers":0,"missing_providers":EXPECTED}
    try: data=json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e: return {"site_key":key,"status":"invalid_json","error":type(e).__name__}
    offers=data.get("offers",[])
    counts=Counter(o.get("provider") for o in offers if o.get("affiliate_link_verified") is True and o.get("image_rights_verified") is True and str(o.get("url","")).startswith("https://") and str(o.get("image_url","")).startswith("https://"))
    missing={k:max(0,v-counts.get(k,0)) for k,v in EXPECTED.items() if counts.get(k,0)<v}
    valid=data.get("status") in {"ready","verified"} and not missing and len(offers)==10
    return {"site_key":key,"status":"ready" if valid else "incomplete","verified_offers":sum(counts.values()),"provider_counts":dict(counts),"missing":missing}

registry=json.loads((ROOT/"config"/"automation_hub_sites.json").read_text(encoding="utf-8-sig"))["sites"]
wp=[s["site_id"] for s in registry if s.get("platform")=="wordpress" and s.get("content_type")=="blog" and s.get("enabled",True) and s["site_id"] not in {"wp_khealth365","wp_krealestate","wp_kworld365","wp_oliveyoung","wp_ksa"}]
blogger=[s["site_id"] for s in registry if s.get("platform")=="blogger" and s.get("content_type")=="blog" and s.get("enabled",True)]
yt_channels=[c for group in YT.get("groups",{}).values() for c in group]
sns_accounts=SNS.get("accounts",[])
platforms={}
for platform in ["TikTok","Instagram","Threads","Facebook"]:
    rows=[a for a in sns_accounts if a.get("platform")==platform]
    platforms[platform]={"registered_or_listed":len(rows),"publish_connected":sum(a.get("publish_connected") is True for a in rows),"identity_verified":sum(a.get("identity_verified") is True for a in rows)}
catalogs=[catalog_status(k) for k in wp+blogger]
report={
 "generated_at":datetime.now(timezone.utc).isoformat(),
 "policy_version":POLICY["policy_version"],
 "affiliate_allocation":EXPECTED,
 "total_offers_per_article":POLICY["per_article_total"],
 "blogs":{"wordpress_registry":len([s for s in registry if s.get("platform")=="wordpress" and s.get("content_type")=="blog" and s.get("enabled",True)]),"wordpress_locked_excluded":5,"wordpress_eligible_excluding_locked":len(wp),"blogger":len(blogger),"catalogs_ready":sum(x["status"]=="ready" for x in catalogs),"catalogs_missing_or_incomplete":sum(x["status"]!="ready" for x in catalogs)},
 "youtube":{"registry_channels":len(yt_channels),"target_channels":YT.get("target_count",POLICY["platform_scope"]["youtube"]["target_channels"]),"identity_verified_channels":sum(bool(c.get("verified")) for c in yt_channels)},
 "social":platforms,
 "catalog_detail":catalogs,
 "live_writes_enabled":False,
 "note":"Preflight only. No posts, videos, or social content were modified."
}
out=ROOT/"reports"/"london-omnichannel-preflight.json"
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"wordpress_eligible":len(wp),"blogger":len(blogger),"youtube_registry":len(yt_channels),"catalogs_ready":report["blogs"]["catalogs_ready"],"catalogs_missing_or_incomplete":report["blogs"]["catalogs_missing_or_incomplete"],"social_publish_connected":{k:v["publish_connected"] for k,v in platforms.items()},"report":str(out)},ensure_ascii=False))
