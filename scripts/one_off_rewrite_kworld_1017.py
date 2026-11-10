"""Rewrite existing Kworld365 post 1017 in place. Never create a second post."""
import os,re,requests
from bs4 import BeautifulSoup
from scripts.economy_text import generate_text
from scripts.editorial_image_guard import filter_wp_images
from scripts.create_manual_wp_draft import ensure_featured_media

SITE="https://kworld365.com"
POST_ID=1017
AUTH=("huh0303@gmail.com",os.environ["KWORLD365COM"])
r=requests.get(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}",auth=AUTH,timeout=35)
r.raise_for_status()
post=r.json()
old_html=post["content"]["rendered"]
soup=BeautifulSoup(old_html,"html.parser")
# Preserve existing closing sections and all affiliate/product elements.
heading=next((h for h in soup.find_all(["h2","h3"]) if "get in touch" in h.get_text(" ",strip=True).lower()),None)
if heading:
    tail=str(heading)+''.join(str(x) for x in heading.next_siblings)
else:
    # If editorial tail cannot be safely identified, do not risk destroying it.
    raise RuntimeError("Cannot identify existing footer/affiliate sections; refusing overwrite")
title=BeautifulSoup(post["title"]["rendered"],"html.parser").get_text(" ",strip=True)
prompt=f"""Write a factual, original, well-researched English K-pop industry feature on the EXACT topic: {title}.
Focus on how agencies plan global touring, venue milestones, production approvals, logistics, realistic fan verification and 2026 planning. Do not invent any actual artist tour announcement, official government policy, ticket date, quotation, or number. Distinguish general industry practice from verified facts. Do not repeat boilerplate headings or sentences. Output HTML only: paragraphs and 4-6 informative h2 headings. No title h1, no images, no affiliate links, no footer. The article text with spaces removed MUST be 2500 to 3000 characters. Aim for 2750 characters. Specific, useful and journalistic, not promotional."""
body=""
for attempt in range(3):
    raw=generate_text(prompt+ (f" Previous draft was {len(re.sub(r'\\s+','',BeautifulSoup(body,'html.parser').get_text(' ',strip=True)))} characters. Rewrite to 2750 characters." if body else ""),language="en")
    body=re.sub(r"^\\s*```(?:html)?|\\s*```\\s*$","",raw.strip(),flags=re.I)
    count=len(re.sub(r"\\s+","",BeautifulSoup(body,"html.parser").get_text(" ",strip=True)))
    print("EDITORIAL_CHAR_COUNT",count)
    if 2500<=count<=3000:break
else:
    raise RuntimeError("Article length failed; original post unchanged")
pexels=os.getenv("PEXELS_API_KEY","")
pixabay=os.getenv("PIXABAY_KEY","")
candidates=[]
if pexels:
    rr=requests.get("https://api.pexels.com/v1/search",params={"query":"kpop concert crowd lightsticks stage","per_page":15},headers={"Authorization":pexels},timeout=20)
    if rr.ok:candidates=[p["src"]["large"] for p in rr.json().get("photos",[]) if p.get("src")]
if not candidates and pixabay:
    rr=requests.get("https://pixabay.com/api/",params={"key":pixabay,"q":"concert crowd stage","image_type":"photo","per_page":20},timeout=20)
    if rr.ok:candidates=[p["largeImageURL"] for p in rr.json().get("hits",[]) if p.get("largeImageURL")]
selected=filter_wp_images(SITE,candidates,AUTH)
if not selected:raise RuntimeError("No unique verified photo available; original post unchanged")
media_id=ensure_featured_media(SITE,os.environ["KWORLD365COM"],selected[0],title)
if not media_id:raise RuntimeError("Featured media upload failed; original post unchanged")
# The featured image is rendered by WordPress theme; no second editorial inline image.
new_html=body+"\\n"+tail
res=requests.post(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}",auth=AUTH,json={"content":new_html,"featured_media":media_id},timeout=45)
res.raise_for_status()
updated=res.json()
assert updated["id"]==POST_ID
print("UPDATED_POST",POST_ID,updated.get("link"),"MEDIA",media_id,"CHARS",count,"STATUS",updated.get("status"))
