from __future__ import annotations

import json

from .db import Store
from .generator import generate_article
from .quality import MIN_SCORE, score_article
from .registry import site_map
from .states import (
    APPROVED, DRAFTING, FAILED, GENERATED, GENERATING, QUALITY_FAILED,
    QUALITY_PASSED, REJECTED, WP_DRAFTED,
)
from .wordpress import create_draft


class ControlCenter:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()
        self.sites = site_map()

    def create(self, site_id: str, keyword: str):
        if site_id not in self.sites:
            raise ValueError("등록되지 않은 WordPress 사이트입니다")
        if len(keyword.strip()) < 3:
            raise ValueError("키워드는 3자 이상 입력하세요")
        return self.store.create_job(site_id=site_id, keyword=keyword)

    def generate(self, job_id: str):
        job = self.store.get(job_id)
        site = self.sites[job["site_id"]]
        feedback = job.get("quality_failures", [])
        self.store.transition(job_id, GENERATING, error="")
        try:
            article = generate_article(site, job["keyword"], feedback)
            job = self.store.transition(
                job_id, GENERATED,
                title=article["title"],
                meta_description=article["meta_description"],
                content_html=article["content_html"],
                labels_json=json.dumps(article["labels"], ensure_ascii=False),
                image_queries_json=json.dumps(article["image_queries"], ensure_ascii=False),
            )
            score, failures = score_article(article, keyword=job["keyword"], target_chars=site.target_chars)
            target = QUALITY_PASSED if score >= MIN_SCORE else QUALITY_FAILED
            return self.store.transition(
                job_id, target,
                quality_score=score,
                quality_failures_json=json.dumps(failures, ensure_ascii=False),
            )
        except Exception as exc:
            self.store.transition(job_id, FAILED, error=str(exc)[:1000])
            raise

    def draft(self, job_id: str):
        job = self.store.get(job_id)
        if job["state"] != QUALITY_PASSED:
            raise ValueError("품질점수 75점 이상인 작업만 WP 초안을 만들 수 있습니다")
        site = self.sites[job["site_id"]]
        self.store.transition(job_id, DRAFTING, error="")
        article = {
            "title": job["title"], "meta_description": job["meta_description"],
            "content_html": job["content_html"], "labels": job["labels"],
            "image_queries": job["image_queries"],
        }
        try:
            result = create_draft(site, job_id=job_id, keyword=job["keyword"], article=article)
            return self.store.transition(
                job_id, WP_DRAFTED,
                wp_post_id=result.post_id,
                wp_edit_url=result.edit_url,
                wp_preview_url=result.preview_url,
                error="",
            )
        except Exception as exc:
            self.store.transition(job_id, FAILED, error=str(exc)[:1000])
            raise

    def approve(self, job_id: str):
        job = self.store.get(job_id)
        if job["state"] != WP_DRAFTED:
            raise ValueError("WordPress 초안이 확인된 작업만 승인할 수 있습니다")
        # Approval is recorded only. This MVP intentionally has no public-write method.
        return self.store.transition(job_id, APPROVED)

    def reject(self, job_id: str):
        job = self.store.get(job_id)
        if job["state"] not in {WP_DRAFTED, QUALITY_PASSED, QUALITY_FAILED}:
            raise ValueError("현재 상태에서는 반려할 수 없습니다")
        return self.store.transition(job_id, REJECTED)

