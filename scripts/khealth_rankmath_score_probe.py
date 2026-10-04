"""k-health365: Rank Math SEO 점수 일괄 재계산 도구 탐색/실행. MODE=probe(경로만 조회) | run(toolsAction update_seo_score)."""
import json, os, requests
BASE = "https://k-health365.com"
AUTH = ("huh0303@gmail.com", os.environ["KHEALTH365COM"])
H = {"User-Agent": "Mozilla/5.0 london-project-claude"}
MODE = os.getenv("MODE", "probe")
out = {}
r = requests.get(f"{BASE}/wp-json/rankmath/v1", auth=AUTH, headers=H, timeout=30)
out["index_http"] = r.status_code
if r.ok:
    routes = list((r.json().get("routes") or {}).keys())
    out["routes"] = [x for x in routes if any(k in x.lower() for k in ("tool", "score", "bulk", "status"))]
if MODE == "run":
    for act in ("update_seo_score",):
        rr = requests.post(f"{BASE}/wp-json/rankmath/v1/toolsAction", auth=AUTH, headers=H, timeout=120, json={"action": act})
        out[act] = {"http": rr.status_code, "body": rr.text[:400]}
print(json.dumps(out, ensure_ascii=False))
