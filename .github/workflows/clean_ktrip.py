import os, requests

pw = os.getenv("KTRIP365COM", "")
print("PW: " + str(bool(pw)) + " len:" + str(len(pw)))

r = requests.get("https://k-trip365.com/wp-json/wp/v2/posts",
                auth=("huh0303@gmail.com", pw),
                params={"per_page":1,"status":"publish"},
                timeout=15)
print("Status: " + str(r.status_code))
print("Total: " + r.headers.get("X-WP-Total","?"))
