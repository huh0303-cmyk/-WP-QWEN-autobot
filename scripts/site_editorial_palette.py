"""Site-specific editorial color palettes; stable per domain, never per article."""
from urllib.parse import urlparse

PALETTES={
"kworld365.com":("#17365d","#d9a441","#f4f7fb"),
"k-health365.com":("#17604a","#31a77a","#eff9f3"),
"koreamedicaltour.com":("#165c79","#31a6c5","#edf8fc"),
"kfinance365.com":("#173f69","#3989d5","#f0f6ff"),
"koreainsurance365.com":("#27456a","#6a8ec5","#f2f6fc"),
"koreacrypto365.com":("#342e66","#8064cb","#f5f2ff"),
"koreainvest365.com":("#244c48","#c29a45","#f7f8f1"),
"koreataxnlaw.com":("#493e56","#9d7aaf","#f7f3f8"),
"k-visa365.com":("#165766","#29a6a5","#f0faf9"),
"studyinkorea365.com":("#64335a","#c678a6","#fff3fa"),
"jobinkorea365.com":("#344e31","#88a95e","#f6faef"),
"krealestate365.com":("#69472c","#c48a52","#fcf6ef"),
"koreawedding365.com":("#783c58","#dc8fa8","#fff4f7"),
"koreanews365.com":("#2e3744","#d14949","#f7f8fa"),
"k-trip365.com":("#135c80","#f0a14a","#f0f9ff"),
}
def palette(domain):
    host=urlparse(domain).hostname if "://" in domain else domain
    host=(host or "").lower().removeprefix("www.")
    return PALETTES.get(host,("#273c58","#6c8da9","#f4f7fa"))
def style_editorial(html,domain):
    from bs4 import BeautifulSoup
    primary,accent,tint=palette(domain)
    soup=BeautifulSoup(html,"html.parser")
    for h in soup.find_all("h2"):
        h["style"]=f"font-size:1.45rem;line-height:1.4;color:{primary};border-left:5px solid {accent};padding:9px 14px;margin:32px 0 16px;background:{tint};font-weight:750"
        if "frequently asked questions" in h.get_text(" ",strip=True).lower():
            h["style"]=f"font-size:1.5rem;color:{primary};border-top:2px solid {accent};border-bottom:1px solid #dbe2e9;padding:15px 0;margin:36px 0 20px"
    for h in soup.find_all("h3"):
        h["style"]=f"font-size:1.12rem;line-height:1.5;color:{primary};margin:20px 0 8px;font-weight:700"
    for p in soup.find_all("p"):
        p["style"]="font-size:1.06rem;line-height:1.9;color:#293545;margin:0 0 19px"
    first=soup.find("p")
    if first:first["style"]=f"font-size:1.13rem;line-height:1.9;color:{primary};background:{tint};border-left:4px solid {accent};padding:20px 22px;margin:0 0 28px"
    return '<section class="kworld-editorial" style="max-width:780px;margin:0 auto;font-family:inherit">'+str(soup)+'</section>'
