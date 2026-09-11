from __future__ import annotations

import html
import re
import time
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

import requests


@dataclass(slots=True)
class PublicationVerification:
    ok: bool
    requested_url: str
    final_url: str = ""
    http_status: int = 0
    title: str = ""
    attempt: int = 0
    error_code: str = ""
    error_message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_title(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip().casefold()


def verify_publication(
    public_url: str,
    expected_title: str = "",
    *,
    site_url: str = "",
    attempts: int = 4,
    timeout: int = 20,
    initial_delay: float = 2.0,
) -> PublicationVerification:
    """Verify that a claimed publication is a real, public article.

    A 200 response is insufficient when a missing permalink redirects to the home
    page. The verifier therefore checks the final path and the expected title too.
    """
    if not public_url:
        return PublicationVerification(False, public_url, error_code="missing_url", error_message="publisher returned no URL")

    expected = _normalize_title(expected_title)
    requested_path = urlparse(public_url).path.rstrip("/")
    site_path = urlparse(site_url).path.rstrip("/") if site_url else ""
    last = PublicationVerification(False, public_url)

    for attempt in range(1, max(1, attempts) + 1):
        if attempt > 1:
            time.sleep(initial_delay * (attempt - 1))
        try:
            response = requests.get(
                public_url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AutomationHub/1.0)"},
            )
            final_url = response.url
            final_path = urlparse(final_url).path.rstrip("/")
            title_match = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.I | re.S)
            page_title = html.unescape(title_match.group(1)).strip() if title_match else ""
            normalized_page_title = _normalize_title(page_title)

            last = PublicationVerification(
                ok=False,
                requested_url=public_url,
                final_url=final_url,
                http_status=response.status_code,
                title=page_title,
                attempt=attempt,
            )
            if response.status_code != 200:
                last.error_code = "http_not_200"
                last.error_message = f"public URL returned HTTP {response.status_code}"
                continue
            if requested_path and final_path in {"", site_path} and final_path != requested_path:
                last.error_code = "redirected_to_home"
                last.error_message = f"permalink redirected to site home: {final_url}"
                continue
            if expected and expected not in normalized_page_title and normalized_page_title not in expected:
                last.error_code = "title_mismatch"
                last.error_message = f"expected title was not found in page title: {page_title!r}"
                continue
            last.ok = True
            return last
        except requests.RequestException as exc:
            last = PublicationVerification(
                ok=False,
                requested_url=public_url,
                attempt=attempt,
                error_code="request_error",
                error_message=str(exc)[:500],
            )
    return last
