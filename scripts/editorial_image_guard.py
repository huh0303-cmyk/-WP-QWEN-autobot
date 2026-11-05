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



def strip_leading_inline_image_block(content):
    """Remove a body-leading image-only block when the theme already shows featured_media.

    Limited to the first content block: later editorial and product images remain.
    """
    import re
    if not content:
        return content
    source = content.lstrip()
    patterns = (
        r"^(<figure\b[^>]*>.*?</figure>\s*)",
        r"^(<p\b[^>]*>\s*<img\b[^>]*>\s*</p>\s*)",
        r"^(<img\b[^>]*>\s*)",
    )
    for pattern in patterns:
        match = re.match(pattern, source, flags=re.IGNORECASE | re.DOTALL)
        if match and re.search(r"<img\b", match.group(1), flags=re.IGNORECASE):
            leading_ws = len(content) - len(content.lstrip())
            return content[:leading_ws] + source[match.end():].lstrip()
    return content


def strip_title_duplicate_lead_image(content, title):
    """Remove only a leading inline hero whose ALT exactly matches the post title.

    WordPress themes render featured_media separately. Some article generators
    already embed the same lead image in body HTML, producing two hero images.
    This deliberately narrow rule preserves all later editorial/product images.
    """
    import html
    import re

    if not content or not title:
        return content
    title_key = " ".join(html.unescape(re.sub(r"<[^>]+>", "", str(title))).split()).casefold()
    source = content.lstrip()
    # Only inspect the very first content block; never sweep the full article.
    patterns = (
        r"^(<figure\b[^>]*>.*?</figure>\s*)",
        r"^(<p\b[^>]*>\s*<img\b[^>]*>\s*</p>\s*)",
        r"^(<img\b[^>]*>\s*)",
    )
    for pattern in patterns:
        match = re.match(pattern, source, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        block = match.group(1)
        image = re.search(r"<img\b[^>]*>", block, flags=re.IGNORECASE | re.DOTALL)
        if not image:
            return content
        alt = re.search(r"""\balt\s*=\s*(['"])(.*?)\1""", image.group(0),
                        flags=re.IGNORECASE | re.DOTALL)
        if not alt:
            return content
        alt_key = " ".join(html.unescape(alt.group(2)).split()).casefold()
        if alt_key == title_key:
            leading_ws = len(content) - len(content.lstrip())
            return content[:leading_ws] + source[match.end():].lstrip()
        return content
    return content
