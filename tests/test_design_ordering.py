import pytest

from src.design_ordering import catalogue, quote_fragment, synthesis_policy


@pytest.mark.parametrize(
    ("length", "price"),
    [(300, 3500), (500, 3500), (501, 3507), (1000, 7000)],
)
def test_quote_applies_the_full_length_tariff(length, price):
    quote = quote_fragment("A" * length, {})
    assert (quote["length_bp"], quote["price_cents"], quote["currency"]) == (length, price, "USD")


@pytest.mark.parametrize("length", [299, 706])
def test_quote_enforces_scenario_length_limits(length):
    with pytest.raises(ValueError, match="300–705 bp"):
        quote_fragment("A" * length, {"max_length_bp": 705})


@pytest.mark.parametrize("motif", ["CAAGT", "ACTTG"])
def test_quote_rejects_complete_motifs_in_both_orientations(motif):
    with pytest.raises(ValueError, match="blocked synthesis motif"):
        quote_fragment("A" * 150 + motif + "C" * 150, {"blocked_motifs": ["CAAGT"]})


def test_quote_normalizes_lowercase_and_whitespace_and_accepts_partial_motifs():
    sequence = ("a" * 150) + "\ncaag\n" + ("c" * 150)
    quote = quote_fragment(sequence, {"blocked_motifs": ["caagt"]})
    assert quote["sequence"] == ("A" * 150) + "CAAG" + ("C" * 150)
    assert quote["price_cents"] == 3500


@pytest.mark.parametrize("sequence", [None, "", "A" * 300 + "N", ">fragment\n" + "A" * 300])
def test_quote_rejects_invalid_dna(sequence):
    with pytest.raises(ValueError, match="DNA sequence"):
        quote_fragment(sequence, {})


def test_catalogue_exposes_integer_cents_and_units_per_published_sku():
    items = catalogue()
    assert {key: (item["sku"], item["price_cents"], item["pack_units"]) for key, item in items.items()} == {
        "taq_polymerase": ("M0273S", 7500, 400),
        "q5_polymerase": ("M0491S", 13800, 100),
        "phusion_polymerase": ("M0530S", 13600, 100),
        "ecori": ("R3101S", 7100, 10000),
    }
    assert synthesis_policy({"max_length_bp": 705})["max_length_bp"] == 705
