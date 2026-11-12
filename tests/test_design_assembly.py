"""Historical assembly controls using an explicitly constructed synthetic fixture."""
import json
from pathlib import Path

import pytest

from src.design_assembly import assemble, digest, load_design_scenarios
from src.design_ordering import quote_fragment


@pytest.fixture
def task():
    return json.loads((Path(__file__).parent / "fixtures/synthetic_design.json").read_text())


def test_exact_target_from_three_overlap_stocks(task):
    target = task["target_sequence"]
    synthesis = task["synthesis"]
    assembly = task["assembly"]
    assert 2 * synthesis["max_length_bp"] - assembly["min_overlap_bp"] < len(target)
    fragments = [target[:395], target[360:717], target[682:]]
    for fragment in fragments:
        assert quote_fragment(fragment, synthesis)["price_cents"] > 0
    assert assemble(fragments, assembly) == target
    with pytest.raises(ValueError, match="terminal overlap"):
        assemble(list(reversed(fragments)), assembly)


def test_exact_target_from_two_restriction_precursors(task):
    target = task["target_sequence"]
    site = target.index("GAATTC")
    precursors = [target[:site + 6] + "TCCGCG", "ACAGCC" + target[site:]]
    for precursor in precursors:
        assert quote_fragment(precursor, task["synthesis"])["price_cents"] > 0

    left, discarded_right = digest(precursors[0], "ecori")
    discarded_left, right = digest(precursors[1], "ecori")
    assert left["right_end"] == right["left_end"] == "AATT"
    assert assemble([left, right], task["assembly"]) == target
    assert assemble([left, discarded_right], task["assembly"]) == precursors[0]
    assert assemble([discarded_left, right], task["assembly"]) == precursors[1]
    with pytest.raises(ValueError, match="incompatible cohesive ends"):
        assemble([left, right["sequence"]], task["assembly"])


def test_designed_motif_blocks_a_length_eligible_order(task):
    # Includes all of the motif but stays comfortably inside the size bounds.
    continuous = task["target_sequence"][400:1000]
    assert task["synthesis"]["blocked_motifs"][0] in continuous
    with pytest.raises(ValueError):
        quote_fragment(continuous, task["synthesis"])


def test_ambiguous_terminal_overlap_is_rejected(task):
    config = task["assembly"] | {"min_overlap_bp": 4, "max_overlap_bp": 6}
    with pytest.raises(ValueError, match="found 3"):
        assemble(["TTAAAAAA", "AAAAAACC"], config)


def test_digest_rejects_a_site_too_close_to_an_end():
    with pytest.raises(ValueError, match="flanking bases"):
        digest("CCGAATTCTGTGGG", "ecori")


def test_scenario_file_accepts_a_new_target_and_recomputes_experiment_length(tmp_path):
    target = "A" * 400 + "GATC" + "T" * 400
    path = tmp_path / "custom.json"
    path.write_text(json.dumps({
        "target_sequence": f"\n{target.lower()}\n",
        "synthesis": {"blocked_motifs": ["gatc"], "max_length_bp": 500},
        "experiments": {"yield_half_life_minutes": 50},
        "budget_cents": 125000,
    }))
    custom, = load_design_scenarios(path)
    assert custom["target_sequence"] == target
    assert custom["synthesis"] == {
        "min_length_bp": 300,
        "max_length_bp": 500,
        "blocked_motifs": ["GATC"],
        "blocked_exons": [],
        "exon_similarity_threshold": 0.8,
    }
    assert custom["experiments"]["target_length_bp"] == len(target)
    assert custom["experiments"]["yield_half_life_minutes"] == 50
    assert custom["budget_cents"] == 125000


def test_scenario_file_rejects_unrelated_motifs(tmp_path):
    path = tmp_path / "custom.json"
    path.write_text(json.dumps({
        "target_sequence": "A" * 300,
        "synthesis": {"blocked_motifs": ["CCC"]},
    }))
    with pytest.raises(ValueError, match="motif must occur in the target"):
        load_design_scenarios(path)
