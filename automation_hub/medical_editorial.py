"""Editorial scope for the medical-qualification Blogger; no external calls."""
from copy import deepcopy
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "config/medical_qualification_editorial.json"


def medical_profile(profile):
    if profile.get("site_key") != "kmedical_job_center":
        return profile
    policy = json.loads(PATH.read_text(encoding="utf-8"))
    result = deepcopy(profile)
    result["language"] = "ko"
    result["medical_editorial"] = policy
    for section in ("wordpress", "blogspot"):
        result[section].update(theme=policy["theme"], persona=policy["persona"],
                               tone=policy["tone"], categories=policy["categories"])
    result["blogspot"]["editorial_funnel"] = {"qualification_rules": policy["rules"], "official_sources": policy["official_sources"]}
    return result


def require_medical_topic(profile, text):
    policy = profile.get("medical_editorial")
    if policy and not any(term in text for term in policy["candidate_terms"]):
        raise ValueError("의료·보건 자격 채널: 지정 자격·직무와 무관한 주제는 작성하지 않습니다.")


def medical_instructions(profile):
    policy = profile.get("medical_editorial")
    if not policy:
        return ""
    return "\n의료·보건 자격 전문 편집 지침(필수):\n" + "\n".join(policy["rules"])
