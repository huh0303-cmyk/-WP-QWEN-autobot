from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import urlparse


IMAGE_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ALT_RE = re.compile(r"\balt\s*=\s*(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class TistoryDraft:
    site_id: str
    site_url: str
    title: str
    content_html: str
    category: str
    search_description: str
    visibility: str = "private"

    def validate(self) -> list[str]:
        errors: list[str] = []
        host = (urlparse(self.site_url).hostname or "").lower()
        if not self.site_id.startswith("tistory_"):
            errors.append("등록되지 않은 Tistory 사이트 ID입니다")
        if not host.endswith(".tistory.com"):
            errors.append("Tistory 주소가 올바르지 않습니다")
        if not self.title.strip():
            errors.append("제목이 비어 있습니다")
        if not self.content_html.strip():
            errors.append("본문이 비어 있습니다")
        if not self.category.strip():
            errors.append("카테고리가 비어 있습니다")
        description = " ".join(self.search_description.split())
        if not 70 <= len(description) <= 150:
            errors.append("검색설명은 공백 포함 70~150자로 작성해야 합니다")
        if self.visibility != "private":
            errors.append("앱 등록기는 비공개 초안만 저장할 수 있습니다")

        for index, image_tag in enumerate(IMAGE_RE.findall(self.content_html), start=1):
            match = ALT_RE.search(image_tag)
            alt = html.unescape(match.group(2)).strip() if match else ""
            if not alt:
                errors.append(f"이미지 {index}의 ALT가 비어 있습니다")
            elif re.search(r"\.(?:png|jpe?g|webp|gif)$", alt, re.IGNORECASE):
                errors.append(f"이미지 {index}의 ALT가 파일명입니다")
            elif alt.casefold() == self.title.strip().casefold():
                errors.append(f"이미지 {index}의 ALT가 제목을 그대로 복사했습니다")
        return errors

    @property
    def blog_name(self) -> str:
        return (urlparse(self.site_url).hostname or "").split(".", 1)[0]

    def editor_url(self, post_id: str | int) -> str:
        return f"https://{self.blog_name}.tistory.com/manage/newpost/{post_id}?type=post"


@dataclass(frozen=True, slots=True)
class TistoryDraftResult:
    post_id: str
    edit_url: str
    status: str = "private"


class TistoryDraftRegistrar:
    """Contract for the authenticated local-browser writer.

    Tistory has no supported write API for this workflow.  The concrete browser
    worker must implement this contract, preserve ``private`` visibility and
    return only after reopening the saved editor URL successfully.
    """

    def save(self, draft: TistoryDraft) -> TistoryDraftResult:
        errors = draft.validate()
        if errors:
            raise ValueError("; ".join(errors))
        raise RuntimeError("Tistory local-browser worker is not connected")
