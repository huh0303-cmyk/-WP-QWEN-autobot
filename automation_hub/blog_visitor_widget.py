"""Shared HTML+JS snippet for the Blogger daily/total visitor counter.

Used by both the future-post pipeline (queue_blogger_rewrite.py) and the
one-off backfill onto already-published posts, so the two never drift apart.
"""
import re

API_BASE = "https://control.korea365.org/api/blog-visits"
MARK = "kh-visit-counter"


def visitor_counter_html(site_key: str, language: str = "ko") -> str:
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "-", site_key)
    today_label = "오늘 방문" if language.startswith("ko") else "Today"
    total_label = "누적" if language.startswith("ko") else "Total"
    loading = "방문자 수 확인 중…" if language.startswith("ko") else "Loading visitor count…"
    return f"""<div id="{MARK}-{safe_key}" style="text-align:center;margin:20px auto 4px;padding:8px 16px;max-width:280px;border-radius:16px;background:rgba(120,120,120,0.08);font-size:12px;color:#888;">{loading}</div>
<script>(function(){{
  var siteKey = "{safe_key}";
  var box = document.getElementById("{MARK}-{safe_key}");
  if (!box) return;
  var today = new Date().toISOString().slice(0,10);
  var flagKey = "dvc_" + siteKey + "_" + today;
  var alreadyCounted = false;
  try {{ alreadyCounted = !!localStorage.getItem(flagKey); }} catch (e) {{}}
  fetch("{API_BASE}/" + siteKey, {{method: alreadyCounted ? "GET" : "POST"}})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      try {{ localStorage.setItem(flagKey, "1"); }} catch (e) {{}}
      box.textContent = "{today_label} " + data.today + " · {total_label} " + data.total;
    }})
    .catch(function() {{ box.style.display = "none"; }});
}})();</script>"""
