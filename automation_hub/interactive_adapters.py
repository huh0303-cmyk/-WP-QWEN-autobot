from __future__ import annotations

from .publishing import PublishJob, PublishResult


class InteractiveEditorPublisher:
    """Fail-safe adapter for platforms without a supported server write API.

    It never reports a post as published. A local, logged-in editor session must
    consume the queued article and return its public URL before success is logged.
    """

    def __init__(self, platform: str, site_id: str, editor_url: str):
        if platform not in {"naver", "tistory"}:
            raise ValueError("interactive adapter supports naver and tistory only")
        self.platform = platform
        self.site_id = site_id
        self.editor_url = editor_url

    def publish(self, job: PublishJob) -> PublishResult:
        errors = job.validate()
        if errors:
            return PublishResult(False, self.platform, self.site_id, job.job_id, "failed", error_code="invalid_job", message="; ".join(errors))
        return PublishResult(
            False,
            self.platform,
            self.site_id,
            job.job_id,
            "local_login_required",
            error_code="official_write_api_unavailable",
            message="A logged-in local browser must complete the editor submission; unattended GitHub Actions publishing is unavailable.",
            extra={"editor_url": self.editor_url, "paid_image_generation": "blocked"},
        )

