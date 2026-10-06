import requests, sys
from bs4 import BeautifulSoup
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.8"}
q = "Korea student visa D-2 extension documents"
def t(name, fn):
    try:
        r = fn(); print(name, r.status_code, len(r.text), r.text[:160].replace("\n", " "))
        return r
    except Exception as e: print(name, "ERR", type(e).__name__, str(e)[:100])
r = t("ddg_html", lambda: requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=UA, timeout=25))
if r: print("  results", len(BeautifulSoup(r.text, "html.parser").select("a.result__a")))
r = t("ddg_lite", lambda: requests.post("https://lite.duckduckgo.com/lite/", data={"q": q}, headers=UA, timeout=25))
r = t("bing", lambda: requests.get("https://www.bing.com/search", params={"q": q}, headers=UA, timeout=25))
if r: print("  results", len(BeautifulSoup(r.text, "html.parser").select("li.b_algo h2 a")))
r = t("google_news_rss", lambda: requests.get("https://news.google.com/rss/search", params={"q": q}, headers=UA, timeout=25))
r = t("wikipedia_api", lambda: requests.get("https://en.wikipedia.org/w/api.php", params={"action": "query", "list": "search", "srsearch": q, "format": "json"}, headers=UA, timeout=25))
r = t("brave", lambda: requests.get("https://search.brave.com/search", params={"q": q}, headers=UA, timeout=25))
r = t("mojeek", lambda: requests.get("https://www.mojeek.com/search", params={"q": q}, headers=UA, timeout=25))
if r: print("  results", len(BeautifulSoup(r.text, "html.parser").select("a.title")))
r = t("hikorea", lambda: requests.get("https://www.hikorea.go.kr", headers=UA, timeout=25))
r = t("studyinkorea", lambda: requests.get("https://www.studyinkorea.go.kr/en/main.do", headers=UA, timeout=25))
