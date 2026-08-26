SITE_SETTINGS_HEADER = [
    "site_id", "platform", "name", "url", "content_type", "group", "enabled",
    "publish_mode", "daily_min", "daily_max", "weekly_min", "weekly_max",
    "min_gap_minutes", "content_profile", "min_chars", "target_chars", "max_chars",
    "persona", "tone", "category_mode", "default_category", "image_mode",
    "image_min", "image_max", "keyword_mode", "affiliate_profile", "secret_name",
]

RUN_LOG_HEADER = [
    "requested_at", "run_id", "site_id", "platform", "job_type", "status",
    "stage", "keyword", "title", "public_url", "http_status", "attempt",
    "error_code", "error_message", "completed_at",
]

KEYWORD_HEADER = [
    "created_at", "site_id", "keyword", "intent", "freshness_score",
    "site_fit_score", "duplicate_safety_score", "revenue_score", "total_score",
    "status", "used_at",
]

RSS_HEADER = [
    "source_id", "newsroom_site_id", "publisher", "feed_url", "language",
    "trust_level", "enabled", "max_age_hours", "last_checked_at", "last_error",
]
