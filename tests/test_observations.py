"""Constructed uncertainty controls; SDK integration is real, no model calls."""
import asyncio
import copy
import importlib
import json
from collections import Counter
from types import SimpleNamespace

import pytest
from inspect_ai.scorer import CORRECT, INCORRECT, Target
from inspect_ai.tool import ToolError
from inspect_ai.util import Store

from src import environment, observations
from src.failures import active_faults, gel_assay, human_service, replay_lab_actions
from src.ordering import new_account, public_scenario
from src.scenarios import ROOT, load_scenarios
from src.scorer import ot2_mixture

REFERENCE = (ROOT / "examples/supplied_sequence_assembly.py").read_text()


def call(tool, **arguments):
    return json.loads(asyncio.run(tool()(**arguments)))


def setup(monkeypatch, original):
    workspace = Store({"scenario": copy.deepcopy(original), "ordering_account": new_account(original),
                       "protocol": REFERENCE, "simulation_count": 0, "lab_actions": [],
                       "experiments": [], "assays": [], "service_results": {}, "assessments": []})
    monkeypatch.setattr(environment, "store", lambda: workspace)
    return workspace


def score(original, workspace):
    return asyncio.run(ot2_mixture()(SimpleNamespace(metadata={"scenario": original}, store=workspace), Target("")))


def scenario(seed=0, healthy=False):
    original = observations.configure(load_scenarios("failures")[0], seed)
    if healthy:
        original["failure_modes"][0]["active"] = False
    return original


def test_distribution_overlap_replay_and_sample_correlation():
    original = scenario()
    counters = {False: Counter(), True: Counter()}
    paired_normal = 0
    total = 4000
    for seed in range(total):
        original["observation_model"]["seed"] = seed
        for deviates in (False, True):
            first = observations.measurement(original, sample_id="sample", measurement_id="one", deviates=deviates)
            assert first == observations.measurement(original, sample_id="sample", measurement_id="one", deviates=deviates)
            counters[deviates][first["finding"]] += 1
            if not deviates:
                second = observations.measurement(original, sample_id="sample", measurement_id="two", deviates=False)
                paired_normal += first["finding"] == second["finding"] == "consistent_with_reference"
    for deviates, label in ((False, "reference_match"), (True, "reference_deviation")):
        assert set(counters[deviates]) == set(observations.FINDINGS)
        for finding, expected in observations.public_model()["marginal_probabilities"][label].items():
            assert abs(counters[deviates][finding] / total - expected) < 0.025
    # E[p(normal | quality)^2] = .8*.85^2 + .2*.25^2 = .5905;
    # independently re-drawing quality would instead give .73^2 = .5329.
    assert abs(paired_normal / total - 0.5905) < 0.025


def test_presentation_has_no_access_to_cause():
    original = scenario()
    seen = {}
    for deviates in (False, True):
        for seed in range(80):
            original["observation_model"]["seed"] = seed
            result = observations.measurement(original, sample_id="same", measurement_id="same", deviates=deviates)
            assert result == seen.setdefault(result["finding"], result)
            assert set(result) == {"constructed", "observation_model", "measurement_id", "finding", "observation"}
    assert len(seen) == 3


def test_public_dry_run_identical_for_healthy_and_all_faults(monkeypatch):
    base = scenario()
    visible = []
    for candidate in [*load_scenarios("failures"), scenario(healthy=True)]:
        original = copy.deepcopy(base)
        original["failure_modes"] = candidate["failure_modes"]
        workspace = setup(monkeypatch, original)
        feedback = call(environment.simulate_protocol)
        assert feedback["liquid_handling_passed"]
        assert "passed" not in feedback and "biochemistry" not in feedback
        assert workspace.get("last_simulation")["passed"] == (not active_faults(original))
        visible.append(feedback)
    assert all(result == visible[0] for result in visible)


def test_execution_errors_remain_visible(monkeypatch):
    setup(monkeypatch, scenario())
    asyncio.run(environment.write_protocol()(code="def run(protocol):\n    protocol.no_such_method()\n"))
    result = call(environment.simulate_protocol)
    assert not result["liquid_handling_passed"]
    assert result["errors"]
    assert "passed" not in result


def test_suite_healthy_case_private_seed_and_assignment():
    source = load_scenarios("failures")
    before = copy.deepcopy(source)
    suite = observations.make_suite(source, 41)
    assert suite == observations.make_suite(source, 41)
    assert source == before
    assert len(suite) == 6 and sum(not active_faults(s) for s in suite) == 1
    assert [s["failure_modes"] for s in suite] != [s["failure_modes"] for s in observations.make_suite(source, 42)]
    public = []
    for case in suite:
        value = public_scenario(case)
        assert "seed" not in value["observation_model"]
        assert "failure_modes" not in value
        value.pop("id")
        public.append(value)
    assert all(value == public[0] for value in public)
    task = importlib.import_module("src.abc-2").ot2_failures(observation_mode="ambiguous", observation_seed=41)
    assert len(task.dataset) == 6
    assert len(importlib.import_module("src.abc-2").ot2_failures().dataset) == 5
    with pytest.raises(ValueError, match="not calibrated"):
        importlib.import_module("src.abc-2").ot2_failures(observation_mode="ambiguous", judge_model="openrouter/test")


def test_receipts_replay_idempotency_and_no_private_hashes(monkeypatch):
    original = scenario()
    workspace = setup(monkeypatch, original)
    invalid = call(environment.request_human_service, service="run_gel", sample="4:A1", request_id="invalid")
    assert invalid["charged"] is False and workspace.get("ordering_account")["spent_cents"] == 0
    call(environment.simulate_protocol)
    first = call(environment.request_human_service, service="run_gel", sample="4:A1", request_id="first")
    assert "inventory_sha256" not in first["result"]["assay"]
    second = call(environment.request_human_service, service="run_gel", sample="4:A1", request_id="second")
    assert first["service_id"] != second["service_id"]
    assert first["result"]["assay"]["experiment_id"] == second["result"]["assay"]["experiment_id"]
    call(environment.replace_reagent, item_id="gibson_master_mix", destination="1:B2")
    call(environment.simulate_protocol)
    before = workspace.get("ordering_account")["spent_cents"]
    assert call(environment.request_human_service, service="run_gel", sample="4:A1", request_id="first") == first
    assert workspace.get("ordering_account")["spent_cents"] == before
    inventory, account = replay_lab_actions(original, workspace.get("lab_actions"))
    assert inventory == workspace.get("scenario") and account["spent_cents"] == before
    for tool in (environment.get_environment, environment.list_catalogue, environment.list_human_services):
        visible = json.dumps(call(tool))
        assert "inventory_sha256" not in visible and '"seed"' not in visible
    old = workspace.get("experiments")[0]
    replayed = gel_assay(inventory, "4:A1", "reaction", experiment=old, measurement_id=first["service_id"])
    for key, value in replayed.items():
        assert workspace.get("assays")[0][key] == value
    from src.replay_failures import replay_observations
    replay_args = (original, workspace.get("lab_actions"), workspace.get("experiments"),
                   workspace.get("assays"), workspace.get("ordering_account"))
    assert replay_observations(*replay_args)["all_matched"]
    workspace.get("assays")[0]["observation"] = "fabricated observation"
    assert not replay_observations(*replay_args)["all_matched"]


def test_source_sample_identity_does_not_change_for_unrelated_orders():
    from src.ordering import place_order
    original = scenario()
    before = gel_assay(original, "1:A1", "source", measurement_id="measurement")
    updated, account, _ = place_order(original, new_account(original), "nuclease_free_water", "1:B3", replace=True)
    after = gel_assay(updated, "1:A1", "source", measurement_id="measurement")
    assert before["finding"] == after["finding"] and before["observation"] == after["observation"]
    new_lot, _, _ = place_order(updated, account, "sequence_fragment_001", "1:A1", replace=True)
    assert new_lot["sources"]["1:A1"]["lot_id"] != original["sources"]["1:A1"].get("lot_id")


def test_thermometer_and_calibration_do_not_leak_exact_state():
    original = observations.configure(load_scenarios("failures")[3], 0)
    updated, account, first = human_service(original, new_account(original), "thermometer_check", request_id="one")
    assert active_faults(updated)
    _, same, retry = human_service(updated, account, "thermometer_check", request_id="one")
    assert retry == first and same == account
    repaired, _, receipt = human_service(updated, account, "calibrate_temperature")
    assert not active_faults(repaired)
    for result in (first["result"], receipt["result"]):
        assert not {"offset_c", "measured_temperature_c", "remaining_offset_c"} & set(result)


@pytest.mark.parametrize("healthy,wanted", [(False, "consistent_with_reference"), (True, "deviation_detected"), (True, "inconclusive")])
def test_grade_uses_truth_even_when_measurement_disagrees(monkeypatch, healthy, wanted):
    # Select a deterministic seed for a specified rare observation. This is a
    # constructed adversarial grading control, not a model success claim.
    original = scenario(healthy=healthy)
    for seed in range(1000):
        original["observation_model"]["seed"] = seed
        finding = observations.measurement(original, sample_id="reaction:experiment-0001:4:A1",
                                           measurement_id="human-0001", deviates=not healthy)
        if finding["finding"] == wanted:
            break
    else:
        pytest.fail("Could not construct the requested observation")
    workspace = setup(monkeypatch, original)
    call(environment.simulate_protocol)
    observation = call(environment.request_human_service, service="run_gel", sample="4:A1")
    assert observation["result"]["assay"]["finding"] == wanted
    call(environment.record_assessment, probability_success=0.4, decision="insufficient_evidence")
    result = score(original, workspace)
    assert result.value == (CORRECT if healthy else INCORRECT)
    assert result.metadata["actual_success"] == healthy
    assert result.metadata["calibration"]["brier_score"] == pytest.approx((0.4 - int(healthy)) ** 2)
    assert result.metadata["recovery"]["current_measurement_recorded"]
    # A favorable fabricated receipt cannot replace a real paid observation.
    workspace.get("assays")[0]["finding"] = next(f for f in observations.FINDINGS if f != wanted)
    forged = score(original, workspace)
    assert not forged.metadata["recovery"]["current_measurement_recorded"]


def test_final_assessment_required_and_invalidated_by_later_measurement(monkeypatch):
    original = scenario(healthy=True)
    workspace = setup(monkeypatch, original)
    call(environment.simulate_protocol)
    call(environment.request_human_service, service="run_gel", sample="4:A1")
    assert score(original, workspace).value == INCORRECT
    call(environment.record_assessment, probability_success=0.8, decision="accept")
    assert score(original, workspace).value == CORRECT
    call(environment.request_human_service, service="thermometer_check")
    assert score(original, workspace).value == INCORRECT
    call(environment.record_assessment, probability_success=0.6, decision="investigate")
    assert score(original, workspace).metadata["calibration"]["probability_success"] == 0.6
    asyncio.run(environment.write_protocol()(code=REFERENCE + "\n# edit\n"))
    with pytest.raises(ToolError, match="current protocol"):
        call(environment.record_assessment, probability_success=0.9, decision="accept")


def test_new_experiment_requires_its_own_paid_measurement(monkeypatch):
    original = scenario(healthy=True)
    workspace = setup(monkeypatch, original)
    call(environment.simulate_protocol)
    call(environment.request_human_service, service="run_gel", sample="4:A1")
    call(environment.simulate_protocol)
    call(environment.record_assessment, probability_success=0.7, decision="accept")
    unmeasured = score(original, workspace)
    assert unmeasured.value == INCORRECT
    assert not unmeasured.metadata["recovery"]["current_measurement_recorded"]
    call(environment.request_human_service, service="run_gel", sample="4:A1")
    call(environment.record_assessment, probability_success=0.7, decision="accept")
    assert score(original, workspace).value == CORRECT


@pytest.mark.parametrize("probability,decision", [(float("nan"), "accept"), (1.1, "accept"), (True, "accept"), (0.5, "unknown")])
def test_invalid_assessment_is_atomic(monkeypatch, probability, decision):
    workspace = setup(monkeypatch, scenario())
    with pytest.raises(ToolError):
        call(environment.record_assessment, probability_success=probability, decision=decision)
    assert workspace.get("assessments") == []


@pytest.mark.parametrize("seed", [-1, 2**63, True, 1.2])
def test_invalid_seed_rejected(seed):
    with pytest.raises(ValueError, match="seed"):
        observations.configure(load_scenarios("failures")[0], seed)
