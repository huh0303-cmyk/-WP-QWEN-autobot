"""Actionable metadata repair instructions; no invented evidence quotas."""
def metadata_feedback(title, meta, keyword):
    issues = []
    if keyword.strip() and keyword.casefold() not in title.casefold():
        issues.append(f"제목에 실제 검색어 '{keyword}'를 자연스럽게 포함하고 본문 내용과 일치시킬 것. 과장이나 키워드 나열 금지.")
    if not 130 <= len(meta) <= 160:
        issues.append(f"META_DESC는 현재 {len(meta)}자. 공백 포함 130~160자의 완결된 설명으로 수정. 본문에 없는 사실 추가 금지.")
    return issues
