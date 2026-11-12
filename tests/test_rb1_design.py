"""Offline controls using the retrieved RB1 reference, not agent rollouts."""
import json

import pytest
from Bio.Seq import Seq

from src.design_assembly import EXON_FILE, load_design_scenarios
from src.design_lab import apply_action, new_lab
from src.design_ordering import exon_similarity, quote_fragment, synthesis_policy


def test_rb1_reference_coordinates_lengths_and_target_agree():
    scenario, = load_design_scenarios()
    reference = json.loads(EXON_FILE.read_text())
    assert reference["transcript"] == "ENST00000267163.6"
    exons = reference["exons"]
    assert len(exons) == 27
    assert min(e["length_bp"] for e in exons) == 31
    assert max(e["length_bp"] for e in exons) == 1893
    assert "".join(e["sequence"] for e in exons) == scenario["target_sequence"]
    assert len(scenario["target_sequence"]) == 4768
    for exon in exons:
        assert exon["length_bp"] == len(exon["sequence"])
        assert exon["length_bp"] == exon["genomic_end"] - exon["genomic_start"] + 1
        assert exon["sequence"] == scenario["target_sequence"][exon["transcript_start"]-1:exon["transcript_end"]]


def test_one_kilobase_cap_applies_even_without_scenario_limit():
    assert quote_fragment("A" * 1000, {})["length_bp"] == 1000
    with pytest.raises(ValueError, match="Requested 1001"):
        quote_fragment("A" * 1001, {})
    with pytest.raises(ValueError, match="1000 bp"):
        synthesis_policy({"max_length_bp": 1001})


@pytest.mark.parametrize("reverse", [False, True])
def test_embedded_exon_and_mutated_exon_cannot_be_ordered(reverse):
    scenario, = load_design_scenarios()
    exon = scenario["synthesis"]["blocked_exons"][16]
    mutated = "".join(("A" if base != "A" else "C") if i % 10 == 0 else base
                      for i, base in enumerate(exon))
    sequence = "A" * 150 + mutated + "C" * 150
    if reverse:
        sequence = str(Seq(sequence).reverse_complement())
    with pytest.raises(ValueError, match="exon similarity"):
        quote_fragment(sequence, scenario["synthesis"])
    lab = new_lab()
    with pytest.raises(ValueError, match="exon similarity"):
        apply_action(scenario, lab, "order_fragment", sequence=sequence)
    assert lab == new_lab()


def test_edit_similarity_handles_threshold_flanks_indels_and_partial_exons():
    exon = "ACGT" * 25
    assert exon_similarity("T" * 120 + exon + "G" * 100, exon) == 1
    assert exon_similarity(exon[:50] + "A" + exon[50:], exon) == pytest.approx(.99)
    policy = {"blocked_exons": ["A" * 100], "exon_similarity_threshold": .8}
    with pytest.raises(ValueError, match="exon similarity"):
        quote_fragment("C" * 110 + "A" * 80 + "C" * 110, policy)
    assert quote_fragment("C" * 110 + "A" * 79 + "C" * 111, policy)
    # A >1 kb exon is evaluated using its full length, rather than a short window.
    assert exon_similarity("A" * 1000, "A" * 1893) < .8


@pytest.mark.parametrize("value", [0, -1, 1.1, True, "0.8", float("nan")])
def test_invalid_similarity_thresholds_fail_closed(value):
    with pytest.raises(ValueError, match="exon_similarity_threshold"):
        synthesis_policy({"exon_similarity_threshold": value})
