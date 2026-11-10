"""One-off editorial replacement of Kworld365 post 1017. Preserve title, tags, category, image."""
import os,re,requests
from bs4 import BeautifulSoup
SITE="https://kworld365.com"
ID=1017
auth=("huh0303@gmail.com",os.environ["KWORLD365COM"])
post_response=requests.get(f"{SITE}/wp-json/wp/v2/posts/{ID}",auth=auth,timeout=30)
post_response.raise_for_status()
post=post_response.json()
assert post["id"]==ID and post["featured_media"], "Missing target or featured image"
ARTICLE = """
<p>A global K-pop tour is not confirmed when an agency identifies an attractive market. It becomes credible only after venue holds, production budgets, travel arrangements and local approvals begin to align. For 2026 planning, the distinction matters: an ambitious expansion roadmap is not the same as an announced concert date.</p>
<h2>What an agency roadmap actually covers</h2>
<p>Tour planning typically starts with audience demand, not a list of stadiums. Promoters compare streaming activity, prior ticket sales, local purchasing power, travel accessibility and the availability of suitable venues. A strong online following may justify further research, but it cannot by itself establish that a city can support a profitable show.</p>

<h2>Venue milestones: from hold to confirmed booking</h2>
<p>A venue inquiry is an early conversation. A provisional hold reserves a possible date subject to competing requests and contract terms. A signed venue agreement is a stronger milestone, but it still does not guarantee a public performance if production, permits or commercial arrangements remain unresolved.</p>
<p>Stadium capacity is only one consideration. Stage dimensions, loading access, roof restrictions, sound limits, audience movement and emergency plans can change the usable seating map. Fans should not treat a venue rumor or an unofficial seating diagram as proof of an upcoming tour.</p>
<h2>Production and cross-border logistics</h2>
<p>Touring teams must decide which equipment travels with the production and which items can be sourced locally. Lighting rigs, video walls, audio systems and stage structures require compatible specifications, trained crews and realistic setup windows. International freight can involve customs documents, temporary import arrangements and insurance.</p>

<h2>Budget decisions and the announcement threshold</h2>

<p>Only an authorized agency, promoter or ticketing partner can confirm the details of a specific show. An industry planning article should not be read as a schedule announcement. Before booking flights or accommodation, fans should verify the artist, city, date, venue and official ticketing channel against primary announcements.</p>
<h2>A practical verification checklist for fans</h2>
<p>Check the artist's official channels and the agency's notices first. Compare the announcement with the named promoter and venue, then follow the ticket link from an official source rather than a resale advertisement. If a date appears only on fan accounts or speculative calendars, treat it as unconfirmed. Keep travel purchases flexible until the relevant details are published.</p>
<h2>Frequently Asked Questions</h2>
<h3>Does a venue hold mean a K-pop concert is confirmed?</h3>
<p>No. A hold is a preliminary scheduling arrangement; a confirmed event requires further agreements and an official announcement.</p>
<h3>Why do agencies announce tour cities at different times?</h3>
<p>Venue negotiations, local rules, production feasibility and promoter agreements may reach completion on different schedules.</p>
<h3>Where should international fans check ticket information?</h3>
<p>Start with the artist or agency's verified announcement and use its linked authorized ticket seller. Avoid assuming that search ads or resale listings are official.</p>
<h3>Can a 2026 tour roadmap predict specific concert dates?</h3>
<p>No. A roadmap explains planning priorities and milestones, not guaranteed performances. Dates must be verified individually.</p>
<p><strong>Editorial note:</strong> This article explains general touring practices. It does not report a newly confirmed tour or ticket sale.</p>
"""
soup=BeautifulSoup(ARTICLE,"html.parser")
plain=soup.get_text(" ",strip=True)
count=len(re.sub(r"\s+","",plain))
assert 2500<=count<=3000, f"Length {count} outside required 2500-3000"
assert len(soup.find_all("h2"))>=5 and len(soup.find_all("h3"))>=4
assert not soup.find("img")
# Only editorial body is replaced. WordPress post metadata (title, tags, categories,
# featured media and any post meta) is intentionally not sent in update.
# Preserve existing trailing contact section if present.
old=BeautifulSoup(post["content"]["rendered"],"html.parser")
heading=next((h for h in old.find_all(["h2","h3"]) if h.get_text(" ",strip=True).lower()=="get in touch"),None)
tail=(str(heading)+"".join(str(x) for x in heading.next_siblings)) if heading else ""
new_html=ARTICLE+tail
res=requests.post(f"{SITE}/wp-json/wp/v2/posts/{ID}",auth=auth,json={"content":new_html},timeout=40)
res.raise_for_status()
updated=res.json()
assert updated["id"]==ID and updated["featured_media"]==post["featured_media"]
assert updated["tags"]==post["tags"] and updated["categories"]==post["categories"]
print("SUCCESS",updated["link"],"EDITORIAL_CHARS",count,"MEDIA",updated["featured_media"],"FAQ",4,"TAGS",len(updated["tags"]))
