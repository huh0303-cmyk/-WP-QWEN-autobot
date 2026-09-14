from __future__ import annotations

import html
import re
from dataclasses import dataclass

from .publishing import PublishJob, PublishResult


def html_to_naver_text(value: str) -> str:
    """Turn queued HTML into readable SmartEditor text without image requests."""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|blockquote)\s*>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n\n".join(line for line in lines if line)


@dataclass(slots=True)
class NaverEditorSelectors:
    title: tuple[str, ...] = (
        "[contenteditable='true'][data-placeholder*='제목']",
        ".se-title-text [contenteditable='true']",
        "textarea[placeholder*='제목']",
    )
    body: tuple[str, ...] = (
        ".se-content [contenteditable='true']",
        ".se-component-content [contenteditable='true']",
        ".se-text-paragraph",
        "[contenteditable='true'][data-placeholder*='내용']",
    )


class NaverLocalPublisher:
    """Publish through a user-owned, persistent local Naver browser session.

    The caller supplies a Playwright Page. Success is returned only after the
    browser reaches a public blog URL; editor interaction alone is never success.
    """

    def __init__(self, site_id: str, editor_url: str, expected_blog_id: str = ""):
        self.site_id = site_id
        self.editor_url = editor_url or "https://blog.naver.com/GoBlogWrite.naver"
        self.expected_blog_id = expected_blog_id.strip()
        self.selectors = NaverEditorSelectors()

    @staticmethod
    def _contexts(page):
        return [page, *page.frames]

    def _first_visible(self, page, selectors: tuple[str, ...]):
        for context in self._contexts(page):
            for selector in selectors:
                locator = context.locator(selector).first
                try:
                    if locator.is_visible(timeout=800):
                        return locator
                except Exception:
                    continue
        return None

    def _verify_destination(self, page) -> None:
        if not self.expected_blog_id:
            return
        expected = self.expected_blog_id.lower()
        current = (page.url or "").lower()
        try:
            document = page.content().lower()
        except Exception:
            document = ""
        if expected not in current and expected not in document:
            raise RuntimeError(
                f"로그인한 네이버 블로그가 destination_id={self.expected_blog_id}와 일치하지 않습니다: {page.url}"
            )

    def fill_editor(self, page, job: PublishJob) -> None:
        page.goto(self.editor_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2500)
        if "nid.naver.com" in (page.url or ""):
            raise RuntimeError("네이버 로그인이 필요합니다. 먼저 login 명령을 실행하세요.")
        self._verify_destination(page)
        title = self._first_visible(page, self.selectors.title)
        body = self._first_visible(page, self.selectors.body)
        if title is None or body is None:
            raise RuntimeError("네이버 SmartEditor 제목/본문 입력칸을 찾지 못했습니다. 편집기 화면을 확인하세요.")
        title.click()
        title.fill(job.title) if hasattr(title, "fill") else title.press_sequentially(job.title)
        body.click()
        body.fill(html_to_naver_text(job.content_html)) if hasattr(body, "fill") else body.press_sequentially(html_to_naver_text(job.content_html))

    def submit(self, page, job: PublishJob) -> PublishResult:
        if not job.publish_now:
            return PublishResult(
                False, "naver", self.site_id, job.job_id, "review_ready",
                error_code="manual_review_requested",
                message="본문 입력 완료. publish_now=FALSE이므로 사용자가 검토 후 발행해야 합니다.",
            )
        publish = page.get_by_role("button", name=re.compile("^발행$|발행하기")).first
        if not publish.is_visible(timeout=3000):
            raise RuntimeError("네이버 발행 버튼을 찾지 못했습니다.")
        publish.click()
        page.wait_for_timeout(1200)
        confirm = page.get_by_role("button", name=re.compile("^발행$|확인|발행하기")).last
        if confirm.is_visible(timeout=1500):
            confirm.click()
        page.wait_for_timeout(3500)
        public_url = page.url or ""
        if "blog.naver.com" not in public_url or "GoBlogWrite" in public_url:
            return PublishResult(
                False, "naver", self.site_id, job.job_id, "verification_required",
                error_code="public_url_not_confirmed",
                message="발행 동작 후 공개 글 URL을 확인하지 못했습니다. 브라우저에서 결과를 확인하세요.",
            )
        return PublishResult(True, "naver", self.site_id, job.job_id, "published", public_url=public_url)

    def publish(self, page, job: PublishJob) -> PublishResult:
        errors = job.validate()
        if errors:
            return PublishResult(False, "naver", self.site_id, job.job_id, "failed", error_code="invalid_job", message="; ".join(errors))
        try:
            self.fill_editor(page, job)
            return self.submit(page, job)
        except Exception as exc:
            return PublishResult(
                False, "naver", self.site_id, job.job_id, "local_attention_required",
                error_code="naver_editor_error", message=str(exc)[:500],
                extra={"editor_url": self.editor_url, "paid_image_generation": "blocked"},
            )
