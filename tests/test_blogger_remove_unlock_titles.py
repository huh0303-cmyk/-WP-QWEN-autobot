from scripts.blogger_remove_unlock_titles import cleaned_title


def test_unlock_family_is_removed_without_leaving_leading_punctuation():
    assert cleaned_title("Unlock Your Korea Career: Practical Steps") == "Your Korea Career: Practical Steps"
    assert cleaned_title("Unlocking Korea's Housing Market") == "Korea's Housing Market"
    assert cleaned_title("Benefits That Unlocked Better Choices") == "Benefits That Better Choices"
