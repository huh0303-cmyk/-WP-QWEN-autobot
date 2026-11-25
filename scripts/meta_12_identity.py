"""Validate authenticated Meta identities without requiring a separate ID setting."""


def validated_user_id(platform, payload, expected_handle, configured_id=""):
    field = "user_id" if platform == "instagram" else "id"
    actual_id = str(payload.get(field, "")).strip()
    actual_handle = str(payload.get("username", "")).strip().lower().lstrip("@")
    if (not actual_id.isdigit()
            or actual_handle != expected_handle.strip().lower().lstrip("@")
            or (configured_id and configured_id != actual_id)):
        raise ValueError("identity mismatch")
    return actual_id


def test_already_attempted(row):
    """A saved reservation blocks retries even when the publication call failed."""
    return bool(row.get("test_public_url") or row.get("test_attempted_at")
                or row.get("test_attempted_at_kst") or row.get("test_status") in
                {"ATTEMPT_RESERVED", "NEEDS_RECONCILIATION", "PUBLISHED"})
