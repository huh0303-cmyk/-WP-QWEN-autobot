from __future__ import annotations

import re
import html
import requests
from urllib.parse import urlparse
from dataclasses import dataclass

from control_center.tistory import TistoryDraft, TistoryDraftResult
from automation_hub.tistory_media import editor_category


@dataclass(slots=True)
class TistoryEditorSelectors:
    title: tuple[str, ...] = (
        "textarea[placeholder*='제목']",
        "input[placeholder*='제목']",
        "textarea#post-title-inp",
    )
    body: tuple[str, ...] = (
        "div.ProseMirror[contenteditable='true']",
        "div[contenteditable='true'][role='textbox']",
        "textarea[name='content']",
        "body#tinymce[contenteditable='true']",
    )


class TistoryLocalPublisher:
    """Tistory writer for a persistent, logged-in local browser profile.

    A successful result means the post was saved with the draft's own
    ``visibility`` (private review-only, or public and actually live),
    reopened, and its administrator edit URL was re-verified.

    2026-09-06 CEO decision: this used to be private-only by design ("the
    owner remains the only person who can make it public"). The CEO
    explicitly asked for Tistory to auto-publish end to end like the other
    platforms, so a draft explicitly marked visibility="public" (see
    control_center.tistory.TistoryDraft, wired from the queue row's
    publish_now/visibility columns) now goes all the way to a live post
    instead of stopping at a private save.
    """

    def __init__(self, draft: TistoryDraft):
        self.draft = draft
        self.selectors = TistoryEditorSelectors()

    @staticmethod
    def _first_visible(page, selectors):
        for context in (page, *page.frames):
            for selector in selectors:
                locator = context.locator(selector).first
                try:
                    if locator.is_visible(timeout=700):
                        return locator
                except Exception:
                    continue
        return None

    @staticmethod
    def _click_named(page, pattern: str, timeout: int = 2500):
        button = page.get_by_role("button", name=re.compile(pattern)).first
        if not button.is_visible(timeout=timeout):
            raise RuntimeError(f"Tistory 버튼을 찾지 못했습니다: {pattern}")
        button.click()

    def _verify_login_and_destination(self, page) -> None:
        current = (page.url or "").lower()
        if "tistory.com/auth/login" in current or "accounts.kakao.com" in current:
            raise RuntimeError("Tistory 로그인이 필요합니다. login 명령을 먼저 실행하세요.")
        expected = self.draft.blog_name.lower()
        if expected not in current:
            raise RuntimeError(f"로그인된 편집기가 대상 블로그({expected})와 다릅니다: {page.url}")

    def _fill_category(self, page) -> None:
        # Tistory's category widget has changed labels several times. Prefer an
        # exact visible category and fail closed instead of silently using none.
        control = page.get_by_role("combobox", name="카테고리 선택")
        if control.is_visible():
            control.click()
        else:
            self._click_named(page, r"카테고리|분류", timeout=2000)
        category = page.get_by_text(editor_category(self.draft.site_id, self.draft.category), exact=True).last
        if not category.is_visible(timeout=2500):
            raise RuntimeError(f"등록된 카테고리를 찾지 못했습니다: {self.draft.category}")
        category.click()

    def _fill_search_description(self, page) -> None:
        field = self._first_visible(page, (
            "textarea[placeholder*='검색 설명']",
            "input[placeholder*='검색 설명']",
            "textarea[name='description']",
        ))
        if field is None:
            # Some skins expose it only after opening the setting panel.
            setting = page.get_by_text(re.compile("검색 설명")).first
            if setting.is_visible(timeout=1200):
                setting.click()
                field = self._first_visible(page, (
                    "textarea[placeholder*='검색 설명']",
                    "input[placeholder*='검색 설명']",
                    "textarea[name='description']",
                ))
        if field is None:
            # The standard Tistory editor derives its snippet from the body;
            # unlike Blogger it has no separate search-description input.
            return
        field.fill(self.draft.search_description)

    def _fill_tags(self, page) -> None:
        field = page.locator("#tagText")
        field.wait_for(state="visible", timeout=5000)
        for tag in self.draft.tags:
            field.fill(tag)
            field.press("Enter")
            page.get_by_text(tag, exact=True).last.wait_for(state="visible", timeout=3000)
        if field.input_value().strip():
            raise RuntimeError("태그 입력이 확정되지 않았습니다")

    def _fill_representative_image(self, page) -> None:
        url = self.draft.representative_image_url
        if urlparse(url).scheme != "https":
            raise RuntimeError("대표 이미지 HTTPS 주소가 필요합니다")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        mime = response.headers.get("content-type", "").split(";")[0]
        extensions = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
        if mime not in extensions or not 500 < len(response.content) <= 10 * 1024 * 1024:
            raise RuntimeError("대표 이미지 파일 형식 또는 크기가 올바르지 않습니다")
        dialog = page.get_by_role("dialog")
        dialog.locator('input[type="file"]').set_input_files({
            "name": "representative." + extensions[mime],
            "mimeType": mime, "buffer": response.content,
        })
        # The publication dialog must show a decoded preview, not just a URL.
        preview = dialog.locator("img").last
        preview.wait_for(state="visible", timeout=15000)
        page.wait_for_function("""() => Array.from(document.querySelectorAll('[role="dialog"] img'))
            .some(img => img.complete && img.naturalWidth > 0)""", timeout=15000)

    def fill(self, page) -> None:
        errors = self.draft.validate()
        if not self.draft.tags or not self.draft.representative_image_url:
            errors.append("태그와 대표 이미지가 준비되어야 발행할 수 있습니다")
        if errors:
            raise ValueError("; ".join(errors))
        editor = f"https://{self.draft.blog_name}.tistory.com/manage/newpost/?type=post"
        page.goto(editor, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(2200)
        self._verify_login_and_destination(page)
        title = self._first_visible(page, self.selectors.title)
        body = self._first_visible(page, self.selectors.body)
        if title is None or body is None:
            raise RuntimeError("Tistory 제목 또는 본문 편집기를 찾지 못했습니다")
        title.fill(self.draft.title)
        body.click()
        # Playwright's insert_html keeps img alt attributes and structured HTML.
        # Tistory's native editor has no Blogger-style search-description field.
        # Preserve the supplied description as the leading summary for excerpts.
        content = '<p data-ke-size="size16">' + html.escape(self.draft.search_description) + '</p>' + self.draft.content_html
        body.evaluate("(node, value) => { node.innerHTML = value; node.dispatchEvent(new InputEvent('input', {bubbles:true, inputType:'insertText'})); }", content)
        self._fill_category(page)
        self._fill_search_description(page)
        self._fill_tags(page)

    def _save(self, page, *, public: bool) -> TistoryDraftResult:
        visibility_label = r"^공개$" if public else r"^비공개$"
        confirm_pattern = r"^공개 발행$|^발행$|^저장$|^완료$" if public else r"^비공개 저장$|^저장$|^완료$"
        self._click_named(page, r"^완료$|저장")
        page.wait_for_timeout(900)
        option = page.get_by_text(re.compile(visibility_label)).last
        if not option.is_visible(timeout=2500):
            raise RuntimeError(f"{'공개' if public else '비공개'} 선택 항목을 찾지 못했습니다")
        option.click()
        self._fill_representative_image(page)
        self._click_named(page, confirm_pattern, timeout=3000)
        page.wait_for_timeout(2500)
        match = re.search(r"/manage/(?:newpost|post)/?(\d+)", page.url or "")
        if not match:
            # Tistory commonly leaves the editor and exposes the id in links.
            # Bind the ID to this title's row, never an arbitrary older edit link.
            title_link = page.get_by_role("link", name=self.draft.title, exact=True)
            if title_link.count() != 1:
                raise RuntimeError("저장한 글의 고유한 목록 행을 확인하지 못했습니다")
            row = title_link.locator("xpath=ancestor::li[1]")
            checkbox_id = row.locator('input[id^="inpCheck"]').get_attribute("id") or ""
            match = re.fullmatch(r"inpCheck(\d+)", checkbox_id)
        if not match:
            raise RuntimeError("저장 후 Tistory 글 ID를 확인하지 못했습니다")
        post_id = match.group(1)
        edit_url = self.draft.editor_url(post_id)
        page.goto(edit_url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(1500)
        self._verify_login_and_destination(page)
        document = page.content()
        title_field = self._first_visible(page, self.selectors.title)
        if title_field is None or title_field.input_value() != self.draft.title:
            raise RuntimeError("저장된 제목 재검증에 실패했습니다")
        saved_body = self._first_visible(page, self.selectors.body)
        if saved_body is None or self.draft.search_description not in saved_body.inner_text():
            raise RuntimeError("저장된 검색 설명 요약문 재검증에 실패했습니다")
        if public:
            live_url = self.draft.public_url(post_id)
            page.goto(live_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(1200)
            if self.draft.title not in (page.content() or ""):
                raise RuntimeError(f"공개 발행 후 실제 공개 페이지 재검증에 실패했습니다: {live_url}")
        return TistoryDraftResult(post_id=post_id, edit_url=edit_url, status="public" if public else "private")

    def save_private(self, page) -> TistoryDraftResult:
        return self._save(page, public=False)

    def save_public(self, page) -> TistoryDraftResult:
        return self._save(page, public=True)

    def publish(self, page) -> TistoryDraftResult:
        self.fill(page)
        return self._save(page, public=self.draft.visibility == "public")
