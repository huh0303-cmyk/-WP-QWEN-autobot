"""
1~5단계를 순서대로 실행하는 파이프라인 오케스트레이터.
"""
import os
from datetime import datetime, timedelta, timezone

from config import DRIVE_FOLDER_ID, DRIVE_SUBFOLDERS
from src import script_generator, script_queue, thumbnail_generator, video_builder, youtube_uploader, notifier
from src.drive_utils import get_drive_service, get_or_create_folder, upload_file
from src.tts_elevenlabs import synthesize_dialogue_with_timeline


def run_pipeline(topic: str, lang: str, steps: list[str], publish_delay_hours: int = 3):
    """
    Claude로 그 자리에서 새 대본을 생성해서 실행하는 방식.
    steps: 실행할 단계 목록. ["script", "video", "thumbnail", "upload", "notify"] 중 선택.
    """
    print(f"\n{'='*50}\nHealth Clinic 파이프라인 시작 (신규 생성) | lang={lang} | topic='{topic}'\n{'='*50}")
    parsed = script_generator.run(topic, lang)
    drive_links = {"script": f"https://drive.google.com/file/d/{parsed['drive_file_id']}/view"}
    return _produce_from_parsed(parsed, lang, steps, publish_delay_hours, drive_links)


def run_pipeline_from_queue(lang: str, steps: list[str], publish_delay_hours: int = 3):
    """
    Drive의 HealthClinic_Queue/manifest.csv 에서 다음 순서(ready 상태)의
    미리 작성된 대본을 하나 꺼내와 실행하는 방식.
    """
    print(f"\n{'='*50}\nHealth Clinic 파이프라인 시작 (큐 사용) | lang={lang}\n{'='*50}")
    parsed = script_queue.fetch_next_ready_script(lang)
    drive_links = {"script": f"https://drive.google.com/file/d/{parsed['drive_file_id']}/view"}
    return _produce_from_parsed(parsed, lang, steps, publish_delay_hours, drive_links)


def _produce_from_parsed(parsed: dict, lang: str, steps: list[str], publish_delay_hours: int, drive_links: dict):
    title = parsed["title"]
    script_text = parsed["script"]
    scene_keywords = parsed["scene_keywords"]
    topic_slug = parsed["topic_slug"]
    print(f"[Pipeline] 대본 준비 완료 → 제목: {title}")

    if "video" not in steps and "thumbnail" not in steps and "upload" not in steps:
        return {"title": title, "drive_links": drive_links}

    # ── 2. 음성 + 영상 합성 ────────────────────
    video_local_path = f"/tmp/{topic_slug}_{lang}.mp4"
    if "video" in steps:
        audio_path, timeline = synthesize_dialogue_with_timeline(script_text, lang)
        video_builder.build_video(script_text, scene_keywords, audio_path, timeline, lang, video_local_path, title=title)

        service = get_drive_service()
        lang_root = get_or_create_folder(service, f"HealthClinic_{lang}", DRIVE_FOLDER_ID)
        videos_folder = get_or_create_folder(service, DRIVE_SUBFOLDERS["videos"], lang_root)
        video_file_id = upload_file(video_local_path, videos_folder)
        drive_links["video"] = f"https://drive.google.com/file/d/{video_file_id}/view"

    # ── 3. 썸네일 생성 ─────────────────────────
    thumbnail_path = f"/tmp/{topic_slug}_{lang}_thumb.jpg"
    if "thumbnail" in steps:
        main_keyword = scene_keywords.split(",")[0].strip() if scene_keywords else title
        thumbnail_generator.generate_thumbnail(title, main_keyword, lang, thumbnail_path)

        service = get_drive_service()
        lang_root = get_or_create_folder(service, f"HealthClinic_{lang}", DRIVE_FOLDER_ID)
        thumb_folder = get_or_create_folder(service, DRIVE_SUBFOLDERS["thumbnails"], lang_root)
        thumb_file_id = upload_file(thumbnail_path, thumb_folder)
        drive_links["thumbnail"] = f"https://drive.google.com/file/d/{thumb_file_id}/view"

    # ── 4. 유튜브 예약 발행 ────────────────────
    video_url = None
    publish_at_iso = None
    if "upload" in steps:
        publish_at = datetime.now(timezone.utc) + timedelta(hours=publish_delay_hours)
        publish_at_iso = publish_at.strftime("%Y-%m-%dT%H:%M:%SZ")

        description = (
            f"{parsed['hook']}\n\n"
            f"이 콘텐츠는 일반 정보 제공 목적이며 의학적 진단이나 치료를 대체하지 않습니다.\n"
            f"자세한 사항은 전문의와 상담하세요.\n\n#HealthClinic"
        )
        video_url = youtube_uploader.upload_and_schedule(
            video_path=video_local_path,
            thumbnail_path=thumbnail_path,
            title=title,
            description=description,
            lang=lang,
            publish_at_iso=publish_at_iso,
        )

    # ── 5. 이메일 알림 ─────────────────────────
    if "notify" in steps and video_url:
        notifier.send_publish_notification(
            lang=lang,
            title=title,
            video_url=video_url,
            publish_at_iso=publish_at_iso,
            drive_links=drive_links,
        )

    print(f"\n{'='*50}\nHealth Clinic 파이프라인 완료\n{'='*50}")
    return {"title": title, "video_url": video_url, "drive_links": drive_links}
