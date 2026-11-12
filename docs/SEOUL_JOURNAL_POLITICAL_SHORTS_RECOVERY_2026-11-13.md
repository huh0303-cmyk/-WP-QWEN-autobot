# Seoul Journal political Shorts recovery — 2026-11-13
Status: Editorial recovery specification and first production brief. NOT a rendered or uploaded video.

## Non-negotiable production rules
- Source-led, daily Korean political confrontation coverage, especially Lee Jae-myung and Han Dong-hoon when the day's reporting supports the story; also other major politicians as relevant.
- Review the owner's supplied KNN reference video for pacing, shot changes, on-screen quote hierarchy and end question. Emulate editorial mechanics only; never copy KNN footage/audio or graphics without an applicable license or permission. Parliamentary video also needs clip-by-clip rights checks.
- 9:16, 1080x1920, 40–60 seconds, hook within 2 seconds; no generic faceless background.
- Use authentic licensed/authorized photos of the correctly identified politicians; source and license attribution, distinct images and image hash checks. If no compliant image, stop.
- 1.5–2.5 second visual changes; animated crop/zoom; narration-aligned captions in 2–3 word chunks, no opaque box over faces.
- TTS shared chain Fish.audio -> Qwen-TTS -> Edge TTS with verified 3 masculine/3 feminine profiles; 1.2x where intelligible. No silent audio.
- End with neutral, specific question and '찬성 / 반대 / 판단 유보'; never fabricate YouTube interactive poll or results.
- Facts and attributed claims only; verify date, speaker, exact quote and event from at least two independent sources when possible; distinguish allegations from established facts.
- Titles without year. Never reuse the same title, footage or hero images within the dedup window.
- First canary: PRIVATE only, inspect MP4 and source receipt, owner approval before resuming scheduled PUBLIC posts.

## First Shorts production brief (fact-check gated)
Working topic: 이재명 공소취소 논쟁 — 한동훈의 비판과 여권 반응
Proposed hook (conditional on verified source): '공소취소 논쟁, 한동훈은 무엇을 문제 삼았을까요?'
Structure:
00–03s: two genuine politician images, concise hook.
03–13s: dated verified statement by Han Dong-hoon, accurately attributed.
13–25s: documented Lee Jae-myung / government or party response, only if available and on record.
25–39s: explain the legal/political point of contention without implying guilt.
39–50s: independently verified current procedural status and what remains disputed.
50–55s: '이 공방, 어떻게 보십니까? 찬성·반대·판단 유보'.
No fabricated quotes, unverified proceedings, or made-up response. Do not render until current sources and rights-cleared assets are attached.

## Diagnostic checklist
1. Compare first three >1,500-view Shorts against latest six: titles, first 3 seconds, photo count/quality, caption timing, TTS, retention if authorized YouTube Analytics data is accessible.
2. Inspect actual scheduled workflow, branch, failure step, channel ID and OAuth upload scope. Do not confuse workflow green status with video publication.
3. Inspect code for wrong story selection (currently first Naver politics card), article-photo-only fallback, Fish->Edge skipping Qwen, font paths and audio/video mux sync.
4. Verify exact Seoul Journal channel ID, create a 1-video PRIVATE canary, capture permalink and QA receipt; do not mass publish.
5. After approval, enable daily three topic-distinct Shorts with individual retry and stop-on-failure gates.

## Sources required per produced episode
- Source URL, publisher, publication time, exact supported claim, photo/video license, original creator attribution and reuse conditions.
- For KNN reference: user-provided reference URL or actual uploaded sample needed to compare shot-by-shot; do not claim reviewed without access.
