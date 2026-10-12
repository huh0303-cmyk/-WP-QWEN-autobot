"""Shared HTML+JS snippet for the Blogger daily/total visitor counter.

Used by both the future-post pipeline (queue_blogger_rewrite.py) and the
one-off backfill onto already-published posts, so the two never drift apart.
"""
import re

API_BASE = "https://control.korea365.org/api/blog-visits"
MARK = "kh-visit-counter"


def visitor_counter_html(site_key: str, language: str = "ko") -> str:
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "-", site_key)
    today_label = "Today pageviews"
    total_label = "Total pageviews"
    loading = "Loading pageviews..."
    return f"""<div id="{MARK}-{safe_key}" style="text-align:center;margin:20px auto 4px;padding:8px 16px;max-width:280px;border-radius:16px;background:rgba(120,120,120,0.08);font-size:12px;color:#888;">{loading}</div>
<script>(function(){{
  var siteKey = "{safe_key}";
  var box = document.getElementById("{MARK}-{safe_key}");
  if (!box) return;
  var visitorId;
  try {{
    visitorId = localStorage.getItem("k365_visitor");
    if (!visitorId) {{ visitorId = crypto.randomUUID(); localStorage.setItem("k365_visitor", visitorId); }}
  }} catch(e) {{ visitorId = null; }}
  var shouldCount = !!visitorId;
  fetch("{API_BASE}/" + siteKey, {{method: shouldCount ? "POST" : "GET",
    body: shouldCount ? new URLSearchParams({{visitor_id: visitorId}}) : undefined}})
    .then(function(r) {{ if (!r.ok) throw new Error("counter unavailable"); return r.json(); }})
    .then(function(data) {{
      box.textContent = "{today_label} " + data.today + " · {total_label} " + data.total;
    }})
    .catch(function() {{ box.style.display = "none"; }});
}})();</script>"""
