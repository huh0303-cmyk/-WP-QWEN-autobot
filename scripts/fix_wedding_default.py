import os, requests
pw = os.environ["KOREAWEDDING365COM"]
r = requests.post("https://koreawedding365.com/wp-json/wp/v2/categories/1",
                   auth=requests.auth.HTTPBasicAuth("huh0303@gmail.com", pw),
                   json={"name": "Uncategorized"}, timeout=20)
with open("fix_wedding_result.txt", "w") as f:
    f.write(f"status={r.status_code} body={r.text[:300]}")
print(r.status_code, r.text[:200])
