"""Rewrite Kworld365 existing posts in place, one at a time, with rollback backups."""
import argparse,json,os,re,time,hashlib
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from scripts.economy_text import generate_text
import gemini_text
from scripts.kworld_weekly_affiliate_footer import replace as attach_weekly_footer
from scripts.site_editorial_palette import style_editorial
from scripts.replicate_image_provider import generate_image_url
from scripts.editorial_image_guard import image_fingerprint, same_photo

SITE="https://kworld365.com"
AUTH=("huh0303@gmail.com",os.environ["KWORLD365COM"])
OUT=Path("artifacts/kworld-rewrites")
OUT.mkdir(parents=True,exist_ok=True)
def plain(html):
    return BeautifulSoup(html,"html.parser").get_text(" ",strip=True)
def chars(html):
    return len(re.sub(r"\s+","",plain(html)))
def style(html):
    soup=BeautifulSoup(html,"html.parser")
    for h in soup.find_all("h2"):
        h["style"]="font-size:1.45rem;line-height:1.4;color:#17365d;border-left:5px solid #d9a441;padding:9px 14px;margin:32px 0 16px;background:#f4f7fb;font-weight:750"
        if "Frequently Asked Questions" in h.get_text():
            h["style"]="font-size:1.5rem;color:#17365d;border-top:2px solid #d9a441;border-bottom:1px solid #dbe2e9;padding:15px 0;margin:36px 0 20px"
    for h in soup.find_all("h3"):
        h["style"]="font-size:1.12rem;line-height:1.5;color:#17365d;margin:20px 0 8px;font-weight:700"
    for p in soup.find_all("p"):
        p["style"]="font-size:1.06rem;line-height:1.9;color:#293545;margin:0 0 19px"
    first=soup.find("p")
    if first:first["style"]="font-size:1.13rem;line-height:1.9;color:#18344e;background:#eef4f8;border-left:4px solid #d9a441;padding:20px 22px;margin:0 0 28px"
    return '<section class="kworld-editorial" style="max-width:780px;margin:0 auto;font-family:inherit">'+str(soup)+'</section>'
def get(url,**kwargs):
    r=requests.get(url,auth=AUTH,timeout=40,**kwargs);r.raise_for_status();return r.json()
def clean_title(title):
    title=re.sub(r"(?<!\d)2026(?!\d)","",title)
    title=re.sub(r"\s+([:;,.!?])",r"\1",title)
    title=re.sub(r"\s{2,}"," ",title)
    return title.strip(" -–—:|,;")
def title_key(t):
    return re.sub(r"[^\w]+", "", clean_title(t).casefold())
def image_bytes(url):
    r=requests.get(url,timeout=35,headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    if len(r.content)<2048:raise ValueError("Invalid image")
    return hashlib.sha256(r.content).hexdigest(),r.content,r.headers.get("Content-Type","image/jpeg").split(";")[0]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--start",type=int,default=0)
    parser.add_argument("--limit",type=int,default=10)
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    items=get(f"{SITE}/wp-json/wp/v2/posts",params={"per_page":100,"orderby":"date","order":"desc","status":"publish","context":"edit"})
    items=[p for p in items if p["id"]!=1017]
    selection=items[args.start:args.start+args.limit]
    print("SELECTED",len(selection),"TOTAL",len(items),flush=True)
    failed=[]
    selected_ids={p["id"] for p in selection}
    used_titles={title_key(plain(p["title"]["rendered"])) for p in items if p["id"] not in selected_ids}
    # Fingerprint every published featured image, regardless of URL, filename, or media ID.
    # Preserve the oldest copy and mark later visually identical photos for replacement.
    known_images=[]
    duplicate_post_ids=set()
    for existing in reversed(items):
        mid=existing.get("featured_media") or 0
        if not mid: continue
        try:
            media=get(f"{SITE}/wp-json/wp/v2/media/{mid}")
            url=media.get("source_url","")
            if not url: continue
            candidate=image_fingerprint(url)
            match=next((entry for entry in known_images if same_photo(candidate,entry["fingerprint"])),None)
            if match:
                duplicate_post_ids.add(existing["id"])
                print("DUPLICATE_IMAGE_CONTENT",existing["id"],"matches_post",match["post_id"],flush=True)
            else:
                known_images.append({"post_id":existing["id"],"media_id":mid,"url":url,"fingerprint":candidate})
        except Exception as exc:
            print("IMAGE_AUDIT_ERROR",mid,str(exc)[:120],flush=True)
    print("DUPLICATE_IMAGE_POSTS",len(duplicate_post_ids),flush=True)
    for post in selection:
        id=post["id"]
        title=clean_title(plain(post["title"]["rendered"]))
        if not title_key(title):
            failed.append({"id":id,"error":"Empty headline"})
            print("FAILED",id,"Empty headline",flush=True)
            continue
        if title_key(title) in used_titles:
            base=title
            for suffix in (" — Editorial Analysis", " — Practical Guide", " — Industry Perspective", f" — Detailed Review {id}"):
                candidate=base+suffix
                if title_key(candidate) not in used_titles:
                    title=candidate
                    print("TITLE_DEDUPED",id,title,flush=True)
                    break
            else:
                failed.append({"id":id,"error":"Unable to generate unique headline"})
                continue
        original=post["content"].get("raw") or post["content"]["rendered"]
        backup={"id":id,"title":title,"content":original,"featured_media":post["featured_media"],"tags":post["tags"],"categories":post["categories"],"meta":post.get("meta",{})}
        (OUT/f"{id}-backup.json").write_text(json.dumps(backup,ensure_ascii=False,indent=2),encoding="utf-8")
        # Do not use unsupported factual claims in old post as new facts.
        prompt=f"""Create a fresh, original, useful English editorial article for a K-pop website, retaining this exact topic/title: {title}. Never include 2026 in the headline.
The original article may contain incorrect or outdated claims. Do not treat it as a verified source. Do not invent announcements, confirmed tour dates, quotes, statistics, award results, tickets, or agency decisions. If the title implies unverified news, clearly distinguish the claim from verified general context and tell readers to check primary sources. Do not imply you independently researched sources.
Write semantic HTML only: 1 introductory paragraph, 5-6 descriptive H2 sections with useful detailed paragraphs, then H2 Frequently Asked Questions with 4 H3 questions and short factual answers. No H1, no images, no footers, no product ads, no markdown fences. Vary the prose naturally and make each section distinct. Aim for 3800 characters WITHOUT whitespace (including FAQ), strict acceptable range 2500-5000. Prioritize real reader utility over keyword stuffing."""
        try:
            article=None
            for attempt in range(3):
                generated=generate_text(prompt,language="en")
                generated=re.sub(r"^\s*```(?:html)?|\s*```\s*$","",generated.strip(),flags=re.I)
                soup=BeautifulSoup(generated,"html.parser")
                h2=soup.find_all("h2");h3=soup.find_all("h3")
                n=chars(generated)
                print("DRAFT",id,"attempt",attempt+1,"chars",n,"h2",len(h2),"h3",len(h3),"model",gemini_text.last_writer_model,flush=True)
                if 2500<=n<=5000 and len(h2)>=5 and len(h3)>=4 and any("frequently asked" in h.get_text().lower() for h in h2):
                    article=generated;break
                prompt+=f" Previous output had {n} nonwhitespace characters, {len(h2)} H2 and {len(h3)} H3. Rewrite completely to meet all limits."
            if article is None:raise ValueError("Editorial quality gate failed")
            # Existing affiliate / product widgets are preserved only if identifiable.
            old=BeautifulSoup(original,"html.parser")
            preserved=[]
            for node in old.find_all(["div","section"]):
                attrs=" ".join(str(v) for v in node.attrs.values()).lower()
                if any(k in attrs for k in ("coupang","affiliate","seoul-mall","seoulmall")):
                    if not any(node in p.descendants for p in preserved):preserved.append(node)
            tail="".join(str(x) for x in preserved)
            output=attach_weekly_footer(style_editorial(article,SITE)+tail)
            if args.dry_run:
                print("DRY_RUN",id,title,"chars",chars(article),flush=True)
                continue
            image_id=post.get("featured_media") or 0
            needs_replacement=post["id"] in duplicate_post_ids
            if needs_replacement:
                print("DUPLICATE_IMAGE_REPLACE",id,image_id,flush=True)
                image_id=0
                for image_attempt in range(4):
                    url=generate_image_url(f"{title}, original K-pop editorial illustration, no lettering, variation {id}-{image_attempt}",theme="K-pop")
                    if not url:continue
                    digest,data,mime=image_bytes(url)
                    candidate=image_fingerprint(url)
                    if any(same_photo(candidate,entry["fingerprint"]) for entry in known_images):
                        print("IMAGE_DUPLICATE_REJECTED",id,image_attempt,flush=True)
                        continue
                    ext=".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"
                    uploaded=requests.post(f"{SITE}/wp-json/wp/v2/media",auth=AUTH,headers={"Content-Disposition":f'attachment; filename="kworld-{id}-{digest[:12]}{ext}"',"Content-Type":mime},data=data,timeout=60)
                    uploaded.raise_for_status()
                    image_id=uploaded.json()["id"]
                    requests.post(f"{SITE}/wp-json/wp/v2/media/{image_id}",auth=AUTH,json={"alt_text":title},timeout=20).raise_for_status()
                    known_images.append({"post_id":id,"media_id":image_id,"url":url,"fingerprint":candidate})
                    break
                if not image_id:raise ValueError("Duplicate image replacement unavailable; this post skipped, other posts continue")
            else:
                print("IMAGE_PRESERVED",id,image_id,flush=True)
            response=requests.post(f"{SITE}/wp-json/wp/v2/posts/{id}",auth=AUTH,json={"content":output,"title":title,"featured_media":image_id},timeout=45)
            response.raise_for_status()
            updated=response.json()
            if updated["id"]!=id or updated["featured_media"]!=image_id or updated["tags"]!=post["tags"] or updated["categories"]!=post["categories"]:
                raise RuntimeError("Post metadata changed unexpectedly")
            used_titles.add(title_key(title))
            print("UPDATED",id,updated["link"],"chars",chars(article),flush=True)
            (OUT/f"{id}-result.json").write_text(json.dumps({"id":id,"url":updated["link"],"chars":chars(article),"model":gemini_text.last_writer_model},ensure_ascii=False),encoding="utf-8")
        except Exception as e:
            failed.append({"id":id,"error":str(e)[:300]})
            print("FAILED",id,type(e).__name__,str(e)[:200],flush=True)
    (OUT/f"failures-{args.start}.json").write_text(json.dumps(failed,indent=2),encoding="utf-8")
    if failed:raise RuntimeError(f"{len(failed)} of {len(selection)} failed: {failed}")
if __name__=="__main__":main()
