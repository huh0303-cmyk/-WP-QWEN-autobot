from control_center.metric_evidence import index_metrics


def test_refresh_error_does_not_erase_verified_index_count():
    result = index_metrics({'audited_at': '2026-09-07T11:40:00Z',
        'summary': {'indexed': 19, 'unindexed': 32, 'unknown': 0, 'indexed_delta': 2, 'total_published': 51},
        'error': 'wp_inventory_failed: Network is unreachable'})
    assert result['indexed'] == 19
    assert result['indexed_delta'] is None
    assert result['index_stale']


def test_verified_zero_is_not_missing():
    result = index_metrics({'audited_at': '2026-09-07',
        'summary': {'indexed': 0, 'unindexed': 5, 'unknown': 0}})
    assert result['indexed'] == 0


def test_all_unknown_never_becomes_zero():
    result = index_metrics({'audited_at': '2026-09-07',
        'summary': {'indexed': 0, 'unindexed': 0, 'unknown': 9}})
    assert result['indexed'] is None


def test_no_evidence_remains_unknown():
    assert index_metrics({'error': 'gsc_property_not_accessible'})['indexed'] is None
