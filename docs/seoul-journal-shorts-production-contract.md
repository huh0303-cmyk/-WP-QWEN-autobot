# Seoul Journal Shorts production contract (2026-11-12)

## Required implementation
1. Collect >=5 DISTINCT licensed/editorially usable, source-attributed photographs of the relevant real politicians before rendering. Verify actual subject, image hashes and source rights. Never repeat one still five times. If fewer than five, stop safely.
2. Full-frame 9:16 photo montage; cuts every 1.5–2.5 seconds; subtle 100–112% alternating zoom in/out and pan. Do not substitute a static background.
3. Narration-aligned captions: one centered line of 2–3 Korean words at a time, high-contrast text stroke only. No opaque central rectangle or oversized headline during narration.
4. Preserve existing high-quality TTS provider and style. Randomize among exactly 3 masculine and 3 feminine voice profiles, verify each voice ID works with its selected provider, and do not silently switch to one fixed voice. Record selected role, not credentials.
5. End with 3–5 second neutral issue-specific viewer question and answer choices. Examples: '오세훈과 장동혁, 어느 입장에 더 동의하십니까?' / '찬성·반대·판단 유보'. Never fabricate poll percentages.
6. An MP4 cannot host clickable live voting by itself. Only display live percentages if an actual supported YouTube poll or linked community poll has been created and confirmed via API/platform. Otherwise provide an honest link/instruction without fake UI.
7. PRIVATE upload only, owner approval before publication. Validate >=5 distinct images, visible faces, motion, captions, correct TTS, poll outro, and source accuracy; block upload on failure.

## Current status
The six-voice list and center-panel removal have been committed to scripts/seoul_journal_shorts_pipeline.py. The five-photo montage, speech timing, and interactive poll integration remain implementation tasks and must not be described as completed.
