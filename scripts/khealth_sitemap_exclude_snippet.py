"""k-health365: Code Snippets 플러그인으로 301 이전 글 40개를 Rank Math 사이트맵에서 제외(글·리다이렉트 불변)."""
import json, os, re, time
import requests

BASE = "https://k-health365.com"
IDS = [3374,3386,3392,3410,3574,3704,3708,3718,3750,3843,3863,3871,3875,3879,3924,3936,3938,3951,3973,3975,3977,
       4036,4038,4042,4798,5528,5531,5764,5768,5772,5773,5776,5786,5866,5868,5889,5891,5894,5903,5916]
AUTH = ("huh0303@gmail.com", os.environ["KHEALTH365COM"])
H = {"User-Agent": "Mozilla/5.0 london-project-claude"}
NAME = "LP: exclude redirected posts from Rank Math sitemap"
CODE = f"""
add_filter( 'rank_math/sitemap/entry', function( $url, $type, $object ) {{
    $ids = array({','.join(map(str, IDS))});
    if ( 'post' === $type && is_object( $object ) && isset( $object->ID ) && in_array( (int) $object->ID, $ids, true ) ) {{
        return false;
    }}
    return $url;
}}, 10, 3 );
add_action( 'init', function() {{
    if ( get_option( 'lp_sitemap_excl_v1' ) ) {{ return; }}
    if ( class_exists( '\\\\RankMath\\\\Sitemap\\\\Cache' ) ) {{ \\RankMath\\Sitemap\\Cache::invalidate_storage(); }}
    update_option( 'lp_sitemap_excl_v1', time() );
}} );
"""


def sitemap_hits(linkset):
    idx = requests.get(BASE + "/sitemap_index.xml", timeout=30, headers=H).text
    urls = set()
    for sm in re.findall(r"<loc>([^<]+)</loc>", idx):
        if "post-sitemap" in sm:
            urls |= set(re.findall(r"<loc>([^<]+)</loc>", requests.get(sm, timeout=30, headers=H).text))
    return len(urls), len(linkset & urls)


def main():
    res = {}
    links = set()
    for pid in IDS:
        r = requests.get(f"{BASE}/wp-json/wp/v2/posts/{pid}?_fields=link", auth=AUTH, headers=H, timeout=30)
        if r.ok:
            links.add(r.json()["link"])
    res["before"] = sitemap_hits(links)
    lst = requests.get(BASE + "/wp-json/code-snippets/v1/snippets", auth=AUTH, headers=H, timeout=30)
    res["list_http"] = lst.status_code
    existing = [s for s in (lst.json() if lst.ok else []) if s.get("name") == NAME]
    body = {"name": NAME, "code": CODE.strip(), "scope": "global", "active": True, "priority": 10,
            "desc": "301로 이전된 글 40개를 사이트맵에서 제외. 글/리다이렉트는 변경 없음. 롤백=이 스니펫 비활성화."}
    if existing:
        r = requests.put(f"{BASE}/wp-json/code-snippets/v1/snippets/{existing[0]['id']}", auth=AUTH, headers=H, json=body, timeout=30)
    else:
        r = requests.post(BASE + "/wp-json/code-snippets/v1/snippets", auth=AUTH, headers=H, json=body, timeout=30)
    res["save_http"] = r.status_code
    res["save_body"] = r.text[:300]
    time.sleep(5)
    requests.get(BASE + "/", headers=H, timeout=30)  # trigger init (cache invalidation)
    time.sleep(5)
    res["after"] = sitemap_hits(links)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
