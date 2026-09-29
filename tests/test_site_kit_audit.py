from scripts.audit_site_kit_compatibility import (
    safe_sitekit_connection,
    safe_sitekit_modules,
)


def test_sitekit_connection_receipt_excludes_credentials_and_ids():
    result = safe_sitekit_connection({
        "connected": True,
        "setupCompleted": True,
        "hasConnectedAdmins": True,
        "siteID": "private-id",
        "siteSecret": "private-secret",
        "accessToken": "private-token",
    })
    assert result == {
        "connected": True,
        "setupCompleted": True,
        "hasConnectedAdmins": True,
    }


def test_sitekit_module_receipt_keeps_only_safe_status_fields():
    result = safe_sitekit_modules([{
        "slug": "search-console",
        "active": True,
        "connected": True,
        "setupComplete": True,
        "settings": {"propertyID": "private"},
    }])
    assert result == [{
        "slug": "search-console",
        "active": True,
        "connected": True,
        "setupComplete": True,
    }]
