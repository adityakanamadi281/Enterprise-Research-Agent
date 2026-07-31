from app.services.research import abstract


def test_inverted_openalex_abstract_is_reconstructed() -> None:
    assert abstract({"AI": [1], "manufacturing": [2], "in": [0]}) == "in AI manufacturing"


def test_missing_abstract_is_explicit() -> None:
    assert "No abstract" in abstract(None)
