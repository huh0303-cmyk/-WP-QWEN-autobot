import os, requests

pw = os.getenv("KTRIP365COM", "")
print("PW exists: " + str(bool(pw)))
print("PW length: " + str(len(pw)))

if pw:
    r = requests.get("https://k-trip365.com/wp-json/wp/v2/posts",
                    auth=("huh0303@gmail.com", pw),
                    params={"per_page":1,"status":"publish"},
                    timeout=10)
    print("API status: " + str(r.status_code))
    print("Total: " + r.headers.get("X-WP-Total","?"))
