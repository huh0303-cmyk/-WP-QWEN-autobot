import os
import socket
import requests

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only_getaddrinfo

SITE = "https://koreanews365.com"
AUTH = ("huh0303@gmail.com", os.environ["KOREANEWS365COM"])
r = requests.get(f"{SITE}/wp-json/code-snippets/v1/snippets", auth=AUTH, timeout=25)
print(r.status_code)
items = r.json()
for it in items:
    print(it.get("id"), it.get("name"), "active=", it.get("active"), "scope=", it.get("scope"), "priority=", it.get("priority"))
