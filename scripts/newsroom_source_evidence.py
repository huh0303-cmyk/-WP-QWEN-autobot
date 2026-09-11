"""Enrich approved GOV.UK leads with their openly licensed official release."""
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


def enrich_source(url, summary):
    parsed = urlparse(str(url or ''))
    if parsed.scheme != 'https' or parsed.netloc != 'www.gov.uk' or not parsed.path.startswith('/government/news/'):
        return summary
    try:
        response = requests.get(url, timeout=15, allow_redirects=False,
                                headers={'User-Agent': 'Korea365 source verification/1.0'})
        if response.status_code != 200:
            return summary
        soup = BeautifulSoup(response.text[:1_000_000], 'html.parser')
        body = soup.select_one('.gem-c-govspeak')
        text = body.get_text(' ', strip=True) if body else ''
        if len(text) < 100:
            return summary
        print(f'Official GOV.UK source body verified: {len(text)} characters')
        return str(summary or '')[:500] + '\nVerified official release excerpt:\n' + text[:4500]
    except requests.RequestException:
        return summary
