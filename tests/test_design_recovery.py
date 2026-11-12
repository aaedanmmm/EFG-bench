"""Constructed recovery controls and adversarial checks; no model calls."""
from copy import deepcopy
import json

import pytest

from src.design_lab import apply_action, grade_lab, new_lab, public_lab
from src.design_recovery import load_recovery_scenarios
from src.design_task import design_fault_recovery, public_design
from src.validate_design_recovery import run_control


@pytest.mark.parametrize("seed", [0, 41, 103])
def test_all_faults_solvable_with_public_feedback(seed):
    scenarios = load_recovery_scenarios(seed)
    assert len(scenarios) == 5
    for scenario in scenarios:
        result = run_control(scenario)
        assert result["after_repair"]["passed"]
        assert result["after_repair"]["spent_cents"] > 0
        assert result["after_repair"]["elapsed_minutes"] > 0
        assert result["after_repair"]["budget_cents"] is None
        assert result["after_repair"]["deadline_minutes"] is None


def test_public_tasks_identical_except_id_and_no_private_feedback():
    inputs = []
    for scenario in load_recovery_scenarios():
        public = public_design(scenario)
        public.pop("id")
        inputs.append(public)
        lab = new_lab()
        target = scenario["target_sequence"]
        for sequence in (target[:500], target[460:960], target[920:]):
            lab, response = apply_action(scenario, lab, "order_fragment", sequence=sequence)
            assert "recovery_fault" not in json.dumps(response)
        lab, _ = apply_action(scenario, lab, "order_reagent", item_id="q5_polymerase")
        lab, response = apply_action(scenario, lab, "run_assembly",
                                     fragment_ids=["dna-1", "dna-2", "dna-3"], polymerase="q5_polymerase")
        for output in (response, public_lab(scenario, lab)):
            encoded = json.dumps(output)
            for field in ("recovery_private", "fault_caused_failure", "recovery_revision", "recovery_fault", "witnessed_failures"):
                assert field not in encoded
    assert all(item == inputs[0] for item in inputs)
    assert [s["recovery_private"] for s in load_recovery_scenarios(0)] != [s["recovery_private"] for s in load_recovery_scenarios(41)]
    assert len(design_fault_recovery().dataset) == 5


@pytest.mark.parametrize("change", ["no_failed_assay", "no_final_assay", "old_product", "late_inventory", "wrong_target"])
def test_replay_rejects_incomplete_or_stale_recovery(change):
    scenario = load_recovery_scenarios()[0]
    actions = deepcopy(run_control(scenario)["actions"])
    if change == "no_failed_assay":
        actions = [a for a in actions if not (a["kind"] == "measure_yield" and a["arguments"]["experiment_id"] == "run-1")]
    elif change == "no_final_assay":
        actions = [a for a in actions if not (a["kind"] == "measure_yield" and a["arguments"]["experiment_id"] == "run-2")]
    elif change == "old_product":
        actions[-1]["arguments"]["experiment_id"] = "run-1"
    elif change == "late_inventory":
        actions.append({"kind": "order_fragment", "arguments": {"sequence": scenario["target_sequence"][:500]}})
    else:
        sequence = actions[0]["arguments"]["sequence"]
        actions[0]["arguments"]["sequence"] = ("A" if sequence[0] != "A" else "T") + sequence[1:]
    assert not grade_lab(scenario, actions)["passed"]


def test_controls_distinguish_stock_from_enzyme_and_equipment():
    for scenario in load_recovery_scenarios():
        report = run_control(scenario)
        receipts = [step["response"] for step in report["public_transcript"]
                    if step["kind"] == "design_recovery_service"]
        kind = scenario["recovery_private"]["kind"]
        if kind == "inactive_polymerase":
            assert any(r.get("finding") == "failed" for r in receipts)
            assert any(r.get("measured_temperature_c") == 50 for r in receipts)
        elif kind in ("damaged_stock", "absent_stock"):
            assert any(not r.get("bands_bp", [1]) for r in receipts)
        else:
            assert any(r.get("measured_temperature_c") in (38, 62) for r in receipts)


def test_rejected_services_atomic_and_topup_does_not_repair():
    scenario = next(s for s in load_recovery_scenarios() if s["recovery_private"]["kind"] == "inactive_polymerase")
    lab, _ = apply_action(scenario, new_lab(), "order_reagent", item_id="taq_polymerase")
    for args in ({"service": "calibrate_temperature"}, {"service": "check_stock", "fragment_id": "missing"},
                 {"service": "positive_control", "polymerase": "not_a_polymerase"}):
        before = deepcopy(lab)
        with pytest.raises(ValueError):
            apply_action(scenario, lab, "design_recovery_service", **args)
        assert lab == before
    lab, _ = apply_action(scenario, lab, "order_reagent", item_id="taq_polymerase")
    lab, result = apply_action(scenario, lab, "design_recovery_service", service="positive_control", polymerase="taq_polymerase")
    assert result["finding"] == "failed"
    lab, _ = apply_action(scenario, lab, "replace_design_reagent", item_id="taq_polymerase")
    lab, result = apply_action(scenario, lab, "design_recovery_service", service="positive_control", polymerase="taq_polymerase")
    assert result["finding"] == "passed"


def test_digest_fault_survives_parent_replacement_and_service_budget_is_atomic():
    scenario = next(s for s in load_recovery_scenarios() if s["recovery_private"]["kind"] == "damaged_stock")
    target = scenario["target_sequence"]
    site = target.index("GAATTC")
    lab = new_lab()
    for sequence in (target[:500], "ACAGCC" + target[site:]):
        lab, _ = apply_action(scenario, lab, "order_fragment", sequence=sequence)
    for enzyme in ("ecori", "taq_polymerase"):
        lab, _ = apply_action(scenario, lab, "order_reagent", item_id=enzyme)
    lab, response = apply_action(scenario, lab, "digest_fragment", fragment_id="dna-2", enzyme="ecori")
    child = response["products"][1]["fragment_id"]
    assert "recovery_fault" not in json.dumps(response)
    lab, _ = apply_action(scenario, lab, "replace_design_stock", fragment_id="dna-2")
    lab, response = apply_action(scenario, lab, "design_recovery_service", service="check_stock", fragment_id=child)
    assert response["smear_range_bp"]
    lab, response = apply_action(scenario, lab, "digest_fragment", fragment_id="dna-2", enzyme="ecori")
    fresh_child = response["products"][1]["fragment_id"]
    lab, response = apply_action(scenario, lab, "design_recovery_service", service="check_stock", fragment_id=fresh_child)
    assert response["bands_bp"]
    before = deepcopy(lab)
    constrained = deepcopy(scenario)
    constrained["budget_cents"] = lab["spent_cents"]
    with pytest.raises(ValueError, match="Insufficient budget"):
        apply_action(constrained, lab, "design_recovery_service", service="thermometer_check")
    assert lab == before
    constrained = deepcopy(scenario)
    constrained["deadline_minutes"] = lab["minutes"]
    with pytest.raises(ValueError, match="deadline"):
        apply_action(constrained, lab, "design_recovery_service", service="thermometer_check")
    assert lab == before


def test_monitoring_only_exceeds_former_limits_without_failing():
    scenario = load_recovery_scenarios()[0]
    actions = [
        *[{"kind": "order_reagent", "arguments": {"item_id": "ecori"}} for _ in range(10)],
        {"kind": "wait", "arguments": {"minutes": 700}},
        *run_control(scenario)["actions"],
    ]
    result = grade_lab(scenario, actions)
    assert result["passed"]
    assert result["spent_cents"] > 40000
    assert result["elapsed_minutes"] > 600
    assert result["cost_efficiency"] is None
    assert result["action_count"] == len(actions)
    assert result["experiment_count"] == 2
    lab = new_lab()
    for action in actions:
        lab, response = apply_action(scenario, lab, action["kind"], **action["arguments"])
        assert response["spent_cents"] == lab["spent_cents"]
        assert "remaining_cents" not in response
    status = public_lab(scenario, lab)
    assert status["spent_cents"] == result["spent_cents"]
    assert "remaining_cents" not in status
    public = public_design(scenario)
    assert "budget_cents" not in public
    assert "deadline_minutes" not in public
