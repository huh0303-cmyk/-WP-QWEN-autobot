"""
Health Clinic 자동 콘텐츠 파이프라인 진입점.

사용 예:
    # 그 자리에서 Claude로 새 대본 생성
    python main.py --lang en --topic "menopause symptom relief for women over 50"

    # 미리 써둔 대본을 드라이브 큐에서 순서대로 꺼내 쓰기 (--topic 불필요)
    python main.py --lang kr --from-queue

    # 특정 단계만
    python main.py --lang jp --from-queue --only video,thumbnail,upload,notify
"""
import argparse

from src.pipeline import run_pipeline, run_pipeline_from_queue

ALL_STEPS = ["script", "video", "thumbnail", "upload", "notify"]


def main():
    parser = argparse.ArgumentParser(description="Health Clinic 콘텐츠 자동 생성 파이프라인")
    parser.add_argument("--lang", required=True, choices=["kr", "en", "jp"], help="채널 언어")
    parser.add_argument("--topic", help="이번 영상 주제 (--from-queue 사용 시 생략 가능)")
    parser.add_argument(
        "--from-queue",
        action="store_true",
        help="Claude로 새로 생성하지 않고, 드라이브 큐(HealthClinic_Queue)에서 다음 순서 대본을 꺼내 씀",
    )
    parser.add_argument(
        "--only",
        default=",".join(ALL_STEPS),
        help=f"실행할 단계(쉼표 구분). 기본값: 전체 ({','.join(ALL_STEPS)})",
    )
    parser.add_argument(
        "--publish-delay-hours",
        type=int,
        default=3,
        help="지금부터 몇 시간 뒤로 예약 발행할지 (기본 3시간)",
    )
    args = parser.parse_args()

    steps = [s.strip() for s in args.only.split(",")]
    invalid = set(steps) - set(ALL_STEPS)
    if invalid:
        raise ValueError(f"잘못된 --only 값: {invalid}. 사용 가능: {ALL_STEPS}")

    if args.from_queue:
        result = run_pipeline_from_queue(
            lang=args.lang,
            steps=[s for s in steps if s != "script"],
            publish_delay_hours=args.publish_delay_hours,
        )
    else:
        if not args.topic:
            raise ValueError("--from-queue를 쓰지 않을 땐 --topic이 필요합니다.")
        result = run_pipeline(
            topic=args.topic,
            lang=args.lang,
            steps=steps,
            publish_delay_hours=args.publish_delay_hours,
        )
    print("\n최종 결과:", result)


if __name__ == "__main__":
    main()
