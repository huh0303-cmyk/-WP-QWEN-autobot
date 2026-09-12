import os
import socket
import requests

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

SITE = "https://koreanews365.com"
AUTH = ("huh0303@gmail.com", os.environ["KOREANEWS365COM"])

css = open("koreanews_masthead_v2.css", encoding="utf-8").read()

php_code = (
    "add_action('wp_head', function() {\n"
    "  echo '<style id=\"kn365-mobile-category-and-newsprint\">' . "
    + repr(css).replace("\\n", "' . \"\\n\" . '") + " . '</style>';\n"
    "});\n"
)

# Simpler & safer: base64-embed the CSS and decode at runtime, avoids any quoting issues.
import base64
css_b64 = base64.b64encode(css.encode("utf-8")).decode("ascii")
php_code = (
    "add_action('wp_head', function() {\n"
    f"  $css = base64_decode('{css_b64}');\n"
    "  echo '<style id=\"kn365-mobile-category-and-newsprint\">' . $css . '</style>';\n"
    "});\n"
)

# deactivate the old broken site-css snippet (id 40) first
r = requests.get(f"{SITE}/wp-json/code-snippets/v1/snippets", auth=AUTH, timeout=25)
r.raise_for_status()
for it in r.json():
    if it.get("name", "").startswith("KN365 mobile category bar + newsprint masthead"):
        requests.put(f"{SITE}/wp-json/code-snippets/v1/snippets/{it['id']}", auth=AUTH,
                      json={"id": it["id"], "active": False}, timeout=25)
        print("deactivated old snippet id", it["id"])

payload = {
    "name": "KN365 mobile category bar + newsprint masthead v3 (2026-09-12, PHP echo)",
    "desc": "Always-visible horizontal category strip on mobile + newsprint-style masthead background.",
    "code": php_code,
    "scope": "global",
    "active": True,
    "priority": 20,
    "tags": ["kn365", "masthead", "2026-09-12"],
}

for attempt in range(3):
    resp = requests.post(f"{SITE}/wp-json/code-snippets/v1/snippets", auth=AUTH, json=payload, timeout=25)
    print(attempt, resp.status_code, resp.text[:300])
    if resp.status_code in (200, 201):
        break
