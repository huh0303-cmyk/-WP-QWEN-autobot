# Seoul Journal execution run — 2026-10-21 (KST)

## Result: blocked before video upload; no false success recorded

### 1) Golden Keyword Calendar
- The configured Google Sheets CSV export was fetched from the URL in `.github/workflows/seoul-journal-daily-shorts.yml`.
- The repository policy requires the row dated 4 days before the current KST date: **2026-10-17**.
- The export returned a calendar headed **“2027 황금 키워드 캘린더”** and its date rows are in 2027. A row beginning `2026-10-17,` was not found.
- Policy says not to silently switch dates. Therefore the five calendar Shorts are **BLOCKED**, not “validated”. The sheet needs a 2026-10-17 row or the owner must explicitly change the calendar rule/source.

### 2) YouTube account verification
- The connected vidIQ account reports only one authorized channel: `UCdA24IuR-JE7qButWv5jLqA`, title **서울국제대학-TOPIK센터**, handle `@seoul_topik1`.
- This is not the requested Seoul Journal channel. No upload was attempted; do not substitute the TOPIK channel.

### 3) Instagram verification
- Prior account audit: `@seoul_jisoo` handle is known, but publishing authorization is missing. No Reel was posted.

### 4) Metricool
- Not used. Reserved for TOPIK vocabulary publishing only, per owner instruction.

### 5) One verified reactive news candidate (not uploaded)
**Topic:** 2026 대한민국 소상공인대회, Oct 23–24 at BEXCO, Busan.
**Primary source:** Yonhap, published 2026-10-21 08:00 KST: https://www.yna.co.kr/amp/view/AKR20261020145500030

**Short script (about 25–30 sec; verify event details again before publication):**
- Hook (0–2s): “이번 주 부산 벡스코, 소상공인 행사가 열립니다.”
- Body: “2026 대한민국 소상공인대회가 10월 23일과 24일, 부산 벡스코에서 열릴 예정입니다. 소상공인 제품 판매전과 업종별 기술 체험이 마련되고, 정부 포상도 진행된다고 주최 측이 밝혔습니다.”
- Close: “방문 전 행사 공식 안내에서 일정과 참여 정보를 확인하세요. 서울저널이 핵심 일정만 전해드립니다.”
- Cover: “10월 23–24일 / 부산 벡스코”
- Description: “2026 대한민국 소상공인대회 일정 안내. 행사 세부 내용은 공식 안내를 확인하세요.”
- Tags: `#소상공인 #부산 #벡스코 #대한민국소상공인대회 #서울저널`
- Status: `SCRIPT_ONLY — not rendered, not uploaded`

### Exact blockers to clear
1. Fix/provide the annual calendar row for 2026-10-17 (or explicitly authorize a different row/date).
2. Connect the correct Seoul Journal YouTube channel to the publishing integration; current authorization is TOPIK only.
3. Authorize the exact Instagram `@seoul_jisoo` publishing account.
4. Configure and verify the approved ElevenLabs voice credential/voice ID before rendering.

**Do not mark any video as created or published until a real MP4 and platform post ID/URL exist.**
