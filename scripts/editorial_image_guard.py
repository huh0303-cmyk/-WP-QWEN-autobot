"""Compare photo content, not URLs, before a WP hero can be reused."""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from io import BytesIO
import hashlib
from urllib.parse import urlparse
import requests
from PIL import Image, ImageOps, ImageStat


def fingerprint(data):
    with Image.open(BytesIO(data)) as original:
        rgb=ImageOps.exif_transpose(original).convert("RGB")
        gray=rgb.convert("L")
        small=list(gray.resize((9,8)).getdata())
        dh=sum((small[y*9+x] > small[y*9+x+1]) << (y*8+x) for y in range(8) for x in range(8))
        pixels=list(gray.resize((8,8)).getdata()); mean=sum(pixels)/64
        ah=sum((p > mean) << i for i,p in enumerate(pixels))
        return {"sha":hashlib.sha256(data).hexdigest(),"dhash":dh,"ahash":ah,"spread":ImageStat.Stat(gray.resize((32,32))).stddev[0]}


def same_photo(a,b):
    if a["sha"] == b["sha"]: return True
    return min(a["spread"],b["spread"]) > 5 and (a["dhash"]^b["dhash"]).bit_count() <= 6 and (a["ahash"]^b["ahash"]).bit_count() <= 6


@lru_cache(maxsize=512)
def image_fingerprint(url):
    if urlparse(url).scheme not in ("http","https"): raise ValueError("Invalid image URL")
    with requests.get(url,timeout=15,stream=True) as response:
        response.raise_for_status()
        if not response.headers.get("Content-Type","").startswith("image/"): raise ValueError("Not an image")
        data=bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data)>12_000_000: raise ValueError("Oversized image")
    return fingerprint(bytes(data))


def recent_posts(site, auth=None):
    r=requests.get(site.rstrip('/')+'/wp-json/wp/v2/posts',auth=auth,params={"per_page":50,"status":"publish","_embed":"wp:featuredmedia"},timeout=30)
    r.raise_for_status()
    return r.json()


def photo_url(post):
    return next((m.get("source_url","") for m in post.get("_embedded",{}).get("wp:featuredmedia",[]) if isinstance(m,dict)),"")


def filter_wp_images(site, images, auth=None):
    if not images: return []
    try:
        urls=list(dict.fromkeys(photo_url(p) for p in recent_posts(site,auth) if photo_url(p)))
        with ThreadPoolExecutor(max_workers=6) as pool:
            known=list(pool.map(image_fingerprint,urls))
        accepted=[]
        for url in images:
            candidate=image_fingerprint(url)
            if any(same_photo(candidate,old) for old in known):
                print("IMAGE_DUPLICATE_BLOCKED: matching recent photo; continue without this image")
                continue
            accepted.append(url);known.append(candidate)
        return accepted
    except Exception as exc:
        print(f"IMAGE_CHECK_UNAVAILABLE: {type(exc).__name__}; no unchecked image attached")
        return []
