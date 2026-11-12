from pathlib import Path
import json
"""Constructed action controls for end-to-end simulator behavior."""
import pytest

from src.design_lab import apply_action, grade_lab, new_lab, public_lab
from src.design_task import public_design


@pytest.fixture
def scenario():
    return json.loads((Path(__file__).parent / "fixtures/synthetic_design.json").read_text())


@pytest.mark.parametrize("restriction", [False, True])
def test_full_workflow_replays_both_routes(scenario, restriction):
    lab = new_lab()

    def act(kind, **args):
        nonlocal lab
        lab, feedback = apply_action(scenario, lab, kind, **args)
        return feedback

    target = scenario["target_sequence"]
    if restriction:
        site = target.index("GAATTC")
        sequences = [target[:site + 6] + "TCCGCG", "ACAGCC" + target[site:]]
    else:
        sequences = [target[:395], target[360:717], target[682:]]
    fragments = [act("order_fragment", sequence=part)["fragment_id"] for part in sequences]
    if restriction:
        with pytest.raises(ValueError, match="Order ecori"):
            act("digest_fragment", fragment_id=fragments[0], enzyme="ecori")
        act("order_reagent", item_id="ecori")
        fragments = [
            act("digest_fragment", fragment_id=fragment, enzyme="ecori")["products"][keep]["fragment_id"]
            for fragment, keep in zip(fragments, (0, 1))
        ]

    with pytest.raises(ValueError, match="Order q5_polymerase"):
        act("run_assembly", fragment_ids=fragments, polymerase="q5_polymerase")
    act("order_reagent", item_id="q5_polymerase")
    run = act("run_assembly", fragment_ids=fragments, polymerase="q5_polymerase")
    assert "initial_yield_ng" not in run
    assert "correct_fraction" not in run
    assert "experiments" not in public_design(scenario)
    assert "initial_correct_yield_ng" not in public_lab(scenario, lab)["experiments"]["run-1"]

    experiment_id = run["experiment_id"]
    act("select_product", experiment_id=experiment_id)
    assert not grade_lab(scenario, lab["actions"])["passed"]
    first = act("measure_yield", experiment_id=experiment_id)
    result = grade_lab(scenario, lab["actions"])
    assert result["passed"] and result["exact_product"]
    assert result["spent_cents"] == (31700 if restriction else 26700)
    assert "correct_yield_ng" not in first

    act("wait", minutes=55)
    if not restriction:
        later = act("measure_yield", experiment_id=experiment_id)
        assert later["yield_ng"] < first["yield_ng"]
    aged = grade_lab(scenario, lab["actions"])
    assert aged["quality_at_submission"]["correct_yield_ng"] < scenario["minimum_correct_yield_ng"]
    assert not aged["passed"]


def test_failed_orders_and_clock_overrun_are_atomic(scenario):
    lab = new_lab()
    with pytest.raises(ValueError, match="blocked synthesis motif"):
        apply_action(scenario, lab, "order_fragment", sequence=scenario["target_sequence"][400:1000])
    assert lab == new_lab()

    lab, _ = apply_action(scenario, lab, "order_reagent", item_id="q5_polymerase")
    lab, _ = apply_action(scenario, lab, "order_reagent", item_id="q5_polymerase")
    with pytest.raises(ValueError, match="Insufficient budget"):
        apply_action(scenario, lab, "order_reagent", item_id="phusion_polymerase")
    assert lab["spent_cents"] == 27600
    assert len(lab["actions"]) == 2

    lab, _ = apply_action(scenario, lab, "wait", minutes=149)
    with pytest.raises(ValueError, match="deadline"):
        apply_action(scenario, lab, "wait", minutes=2)
    assert lab["minutes"] == 149
    assert len(lab["actions"]) == 3


def test_wrong_but_assembled_candidate_can_have_mass_without_correct_yield(scenario):
    target = scenario["target_sequence"]
    lab = new_lab()
    stocks = []
    for part in ["ACGT" + target[4:395], target[360:717], target[682:]]:
        lab, receipt = apply_action(scenario, lab, "order_fragment", sequence=part)
        stocks.append(receipt["fragment_id"])
    lab, _ = apply_action(scenario, lab, "order_reagent", item_id="taq_polymerase")
    lab, _ = apply_action(scenario, lab, "run_assembly", fragment_ids=stocks, polymerase="taq_polymerase")
    lab, reading = apply_action(scenario, lab, "measure_yield", experiment_id="run-1")
    lab, _ = apply_action(scenario, lab, "select_product", experiment_id="run-1")
    result = grade_lab(scenario, lab["actions"])
    assert reading["yield_ng"] > 0
    assert result["quality_at_submission"]["correct_yield_ng"] == 0
    assert not result["passed"]
