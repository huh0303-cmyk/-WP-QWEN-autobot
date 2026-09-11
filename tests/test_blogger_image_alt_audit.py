from scripts.audit_blogger_image_alt import image_audit


def test_image_audit_counts_only_missing_or_blank_alt():
    count, missing = image_audit(
        '<p><img src="a.jpg" alt="Useful description"></p>'
        '<img src="b.jpg" alt="">'
        '<img src="c.jpg">'
    )
    assert count == 3
    assert [item["image_index"] for item in missing] == [1, 2]

