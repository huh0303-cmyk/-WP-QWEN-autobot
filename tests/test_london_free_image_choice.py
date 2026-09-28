from scripts import replicate_image_provider as images


def test_free_default_never_uses_paid_prediction(monkeypatch):
    import stock_image_provider
    monkeypatch.setattr(stock_image_provider, "find_stock_image", lambda *args, **kwargs: None)
    monkeypatch.setattr(images, "_create_prediction", lambda *args: (_ for _ in ()).throw(AssertionError("paid prediction")))
    assert images.generate_image_url("test topic", mode="auto_free") is None


def test_image_choice_rejects_unknown_model():
    try:
        images.generate_image_url("test topic", mode="unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported image model accepted")
