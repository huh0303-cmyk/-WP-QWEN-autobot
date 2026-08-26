SITE_SETTINGS_HEADER = [
    "site_id", "platform", "name", "url", "content_type", "group", "enabled",
    "publish_mode", "daily_min", "daily_max", "weekly_min", "weekly_max",
    "min_gap_minutes", "content_profile", "min_chars", "target_chars", "max_chars",
    "persona", "tone", "category_mode", "default_category", "image_mode",
    "image_min", "image_max", "keyword_mode", "affiliate_profile", "secret_name",
    "language", "timezone", "allowed_categories", "rss_sources",
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

PLATFORM_ACCOUNT_HEADER = [
    "account_id", "platform", "site_id", "display_name", "destination_id",
    "editor_url", "auth_profile", "enabled", "notes",
]

PUBLISH_QUEUE_HEADER = [
    "created_at", "job_id", "site_id", "status", "publish_now", "title",
    "content_html", "labels", "source_keyword", "public_url", "remote_id",
    "error_code", "message", "completed_at",
]

YOUTUBE_CHANNEL_HEADER = [
    "channel_key", "channel_type", "display_name", "channel_id", "secret_profile",
    "workflow", "enabled", "interval_days_min", "interval_days_max",
    "publish_delay_hours", "allowed_hour_start", "allowed_hour_end", "topic_mode",
    "language", "tone", "next_run_at", "last_dispatched_at", "last_run_status",
]

YOUTUBE_RUN_HEADER = [
    "requested_at", "channel_key", "channel_type", "workflow", "status",
    "github_run_url", "scheduled_publish_at", "video_url", "error_message",
]
