# TOPIK QUIZ PLATFORM — PHASE 2

Status: PM BACKLOG / NOT FOR IMMEDIATE LARGE-SCALE EXECUTION
Owner: ChatGPT PM
Implementation: Work/Codex after current normalization and measurement priorities

## Purpose
Convert existing TOPIK social reach and quiz engagement into an owned learning loop with cumulative student progress, reusable digital rewards, and future education/lead monetization.

## Core funnel
Daily/weekly TOPIK social quiz content
-> learner visits quiz page
-> enters minimum identifying information / signs in
-> takes 10–20 vocabulary questions based on recently taught quiz content
-> instant grading
-> correct/incorrect review
-> cumulative score and learning history saved
-> rewards unlocked at milestones
-> free beginner TOPIK lesson/PDF/mock test
-> optional digital-product and KStudy365/study funnel later

## MVP V1
Do not overbuild.

Required:
- 20-question single-answer vocabulary test
- learner nickname/name plus a safer unique identifier mechanism; do not rely on name alone
- instant automatic grading
- score shown immediately
- wrong-answer review
- cumulative score stored
- attempt date/history stored
- Google Sheet logging or similarly low-cost persistent backend
- simple reward threshold logic
- reward can be free PDF / beginner TOPIK lesson / extra test; no cash reward required
- mobile-first UI
- Korean/Vietnamese learner usability considered
- no unnecessary paid API dependency

## Question-bank architecture
Create a reusable TOPIK_WORD_BANK so daily social quiz content is not discarded.

Each word/question record should include where practical:
- question_id
- Korean word
- Vietnamese/English meaning as appropriate
- distractors
- correct answer
- difficulty
- topic/category
- source/lesson date
- social-content linkage
- status/reviewed flag

Weekly test should be able to draw from words actually taught during the week.

## Progress model
Initial simple levels may be used, e.g. Starter / Challenger / Master, but avoid gimmicks that distract from learning.

Possible milestone rules:
- weekly score threshold
- cumulative points threshold
- consecutive participation
- completion streak

Rewards should be low-cost digital assets.

## Privacy / identity rule
Do not ask learners to post email/phone in public comments.
Do not identify learners by name alone.
Use minimum necessary personal information and clear consent where contact collection is involved.
Prefer owned-audience opt-in through a form/login flow.

## Future V2
Only after V1 works end-to-end:
- Google/social login
- streaks
- badges
- weekly leaderboard with privacy-safe display names
- personal vocabulary notebook
- spaced review of missed words
- difficulty adaptation
- teacher/admin dashboard

## Future V3 monetization
Only after usage is proven:
- free quiz -> free resource -> paid workbook/vocabulary pack/mock test/course
- study-abroad / KStudy365 lead where relevant
- cohort/challenge product
- subscription only if learner retention data justifies it

## Success metrics
- quiz starts
- completion rate
- average score
- repeat-test rate
- 7-day returning learners
- reward unlock rate
- free-resource opt-in rate
- later digital-product conversion
- later qualified education/study leads

## Guardrails
- Do not build a large custom platform before validating learner demand.
- Do not add expensive SaaS/API without approval.
- Do not expose personal data.
- Do not auto-message users in spammy ways.
- Do not use unreviewed AI-generated answer keys for production tests.
- Human review is required for question-bank quality before production use.

## Codex implementation rule
This is Phase 2. Do not start implementation until Priority 1–4 in PM_CURRENT_STATUS.md are stable or the user/PM explicitly promotes this ticket.
When promoted, build V1 only first and demonstrate one complete learner flow before adding features.
