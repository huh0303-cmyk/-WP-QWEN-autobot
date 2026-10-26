# Editorial Title Diversity Gate — London Project

## Problem
Generated titles often begin with generic gerunds such as “Understanding”, “Navigating”, “Managing”, or “Preparing”. A title may be grammatically correct and still look machine-produced when the same abstract opening is repeated across many sites.

## Root cause in the publishing workflow
The existing system already has a title gate and a repetition guard, but their checks focus on within-title duplication, stock phrases, “How” openings, and recent-title similarity. The specific generic gerund openings were not explicitly identified as a failure. A title can therefore pass even if it uses one of these stock opening patterns.

## Required workflow
1. **Generate a topic-first title**: include the actual subject, a reader decision, a change, a comparison, a concrete result, or a useful question. Do not begin with an abstract “-ing” label by default.
2. **Check title history**: compare with recent titles on the same site and, where available, across the network. Reject repeated first-phrase patterns and near-duplicates.
3. **Run deterministic gate**: call `title_cliches()` / `title_self_issues()` before any post is saved. Generic gerund openings such as Understanding, Navigating, Managing, Preparing, Exploring, Discovering, and Learning are rejected for rewrite.
4. **Rewrite once with explicit alternatives**: ask the writer for a concrete subject-led title, a question, a comparison, a number only when supported, or a specific outcome. Do not simply replace one gerund with another.
5. **Re-run all checks**: language, factual support, title length, repeated opening, duplicate/near-duplicate, cliché, and body checks. If still failing, do not publish; send to retry/error queue.
6. **Do not mutate old published titles automatically**: use the existing `scripts/retitle_repeated.py` in dry-run first, review the report, and only apply approved changes with `APPLY_CHANGES=true`. Keep newsroom headlines factual and exempt from blog-title rewriting where already configured.
7. **Measure**: report counts for generic-gerund openings, repeated first 1–3 words, exact/near duplicates, rejected titles, retries, and final pass rate.

## Examples
- Avoid: “Understanding Korea’s Rental Deposit System”
- Prefer: “Korea Rental Deposits: What Tenants Pay Before Moving In”
- Avoid: “Navigating Health Insurance Options”
- Prefer: “Which Health Insurance Covers Foreign Residents in Korea?”
- Avoid: “Managing Tax Obligations for Freelancers”
- Prefer: “Freelancers in Korea: Tax Deadlines and Required Filings”
- Avoid: “Preparing for a Korean University Application”
- Prefer: “Korean University Applications: Documents to Prepare First”

These are structural examples, not fixed templates to reuse.

## Acceptance tests
- Titles beginning with the listed generic gerunds fail the deterministic gate.
- Specific subject-led titles pass the gerund-opening check.
- Newsroom titles remain factual and use their existing source-evidence gate.
- A failed title never silently bypasses the gate; rewrite or stop publication.
- Existing post title, slug, body, and status are unchanged unless an explicitly reviewed retitle job is run.

## Scope
Apply this policy to the shared publishing paths for WordPress and Blogger. Confirm the gate is called in every active writer/queue path before enabling or changing scheduled publishing. Do not add paid APIs or paid services.
