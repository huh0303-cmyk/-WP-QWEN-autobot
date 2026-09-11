import os, requests
pw = os.environ.get("KTRIP365COM")
auth = requests.auth.HTTPBasicAuth("huh0303@gmail.com", pw)
r = requests.get("https://k-trip365.com/wp-json/wp/v2/themes", auth=auth, params={"status":"active"}, timeout=20)
print("status:", r.status_code)
if r.status_code == 200 and r.json():
    t = r.json()[0]
    print("theme:", t.get("name",{}).get("rendered"), t.get("stylesheet"), t.get("version"))
else:
    print(r.text[:300])
with open("ktrip_theme_check.txt","w",encoding="utf-8") as f:
    f.write(f"status={r.status_code}\n{r.text[:500]}")
