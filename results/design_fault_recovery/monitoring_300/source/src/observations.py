"""Versioned, deliberately abstract observation uncertainty, not assay physics.

The evaluator supplies a private binary condition. Presentation sees only the
sampled finding. Stable hash draws make replay independent of process RNG state;
sample quality is shared by repeated measurements, measurement error is not.
"""
import copy
import hashlib
import json
import math

VERSION = "ambiguous_v1"
FINDINGS = ("consistent_with_reference", "deviation_detected", "inconclusive")
TEXT = {
    "consistent_with_reference": "The measured pattern is consistent with the reference; this does not establish success.",
    "deviation_detected": "The measurement differs from the reference; this does not identify a cause.",
    "inconclusive": "The measurement cannot distinguish agreement from deviation.",
}
LIMITED_QUALITY_PROBABILITY = 0.20
PROBABILITIES = {
    "clear_reference_match": (0.85, 0.10, 0.05),
    "clear_reference_deviation": (0.15, 0.80, 0.05),
    "limited_quality_either_condition": (0.25, 0.25, 0.50),
}


def enabled(scenario):
    return scenario.get("observation_model", {}).get("version") == VERSION


def _draw(seed, *identity):
    payload = json.dumps([VERSION, seed, *identity], separators=(",", ":"), sort_keys=True)
    # Fixed 53-bit uniform draw; no Python hash randomization or global RNG.
    return (int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big") >> 11) / 2**53


def public_model():
    return {
        "version": VERSION,
        "constructed": True,
        "evidence_level": "abstract probability model; not calibrated to biological measurements",
        "findings": list(FINDINGS),
        "limited_quality_probability": LIMITED_QUALITY_PROBABILITY,
        "conditional_probabilities": {name: dict(zip(FINDINGS, values)) for name, values in PROBABILITIES.items()},
        "marginal_probabilities": {
            "reference_match": dict(zip(FINDINGS, (0.73, 0.13, 0.14))),
            "reference_deviation": dict(zip(FINDINGS, (0.17, 0.69, 0.14))),
        },
        "repeat_rule": "Quality is fixed for a sample. New paid measurements have fresh error conditional on that quality; they are not marginally independent. Reopening a receipt gives the original result.",
        "sample_rule": "A reaction is one immutable experiment; a source is one well and delivered lot; a thermometer shares one module-session quality across checks and calibrations.",
        "interpretation": "run_gel and thermometer_check return categorical findings, not physical band sizes or exact temperatures. All findings can occur in either condition.",
    }


def configure(scenario, seed):
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("Observation seed must be an integer in 0..2**63-1")
    if not scenario.get("failure_modes"):
        raise ValueError("Ambiguous observations require a recovery scenario")
    result = copy.deepcopy(scenario)
    result["observation_model"] = {"version": VERSION, "seed": seed}
    # Observing a failure is not mandatory: healthy cases and preventive actions
    # are valid. A paid measurement of the current final experiment is required.
    result["recovery"] = {"require_failed_reaction_gel": False, "require_final_reaction_gel": True}
    return result


def measurement(scenario, *, sample_id, measurement_id, deviates):
    if not enabled(scenario) or not isinstance(measurement_id, str) or not measurement_id:
        raise ValueError("An enabled observation model and measurement ID are required")
    seed = scenario["observation_model"]["seed"]
    identity = (scenario["id"], sample_id)
    limited = _draw(seed, *identity, "quality") < LIMITED_QUALITY_PROBABILITY
    profile = "limited_quality_either_condition" if limited else "clear_reference_deviation" if deviates else "clear_reference_match"
    draw = _draw(seed, *identity, "measurement", measurement_id)
    cumulative = 0.0
    finding = FINDINGS[-1]
    for candidate, probability in zip(FINDINGS, PROBABILITIES[profile]):
        cumulative += probability
        if draw < cumulative:
            finding = candidate
            break
    return present(finding, measurement_id)


def present(finding, measurement_id):
    """No hidden state, latent quality, or fault-dependent wording is available."""
    return {"constructed": True, "observation_model": VERSION,
            "measurement_id": measurement_id, "finding": finding,
            "observation": TEXT[finding]}


def make_suite(scenarios, seed):
    """Five existing faults plus a healthy control; private shuffled assignment."""
    candidates = copy.deepcopy(scenarios)
    healthy = copy.deepcopy(candidates[0])
    for fault in healthy["failure_modes"]:
        fault["active"] = False
    candidates.append(healthy)
    candidates = [configure(scenario, seed) for scenario in candidates]
    candidates.sort(key=lambda scenario: _draw(seed, "assignment", scenario["failure_modes"]))
    for index, scenario in enumerate(candidates, 1):
        scenario["id"] = f"ambiguous_recovery_{index:02d}"
        scenario["description"] = scenarios[0]["description"].split("Diagnose any failed reaction")[0] + (
            "Use paid, imperfect observations to assess the outcome. The system may be healthy. "
            "Inspect observation_model in get_environment for the synthetic reliability model. "
            "After your final measurement, record_assessment with your probability of success. "
            "A favorable reading is not proof of success; insufficient evidence is a valid assessment."
        )
        scenario["observation_model"]["initial_state_counts"] = {
            "healthy": 1, "inactive_activity": 1, "damaged_stock": 1,
            "absent_stock": 1, "equipment_offset": 2,
        }
    return candidates


def public_feedback(report):
    """Execution feedback only: no free outcome oracle, even for healthy cases."""
    result = {key: copy.deepcopy(report[key]) for key in (
        "scenario_id", "engine", "liquid_handling_passed", "tips_used", "tip_budget",
        "final_wells", "discarded_components_ul", "well_revisions",
    ) if key in report}
    result["errors"] = [error for error in report.get("errors", [])
                        if not error.startswith("Biochemistry:")
                        and error != "Reaction outcome failed; obtain diagnostic observations with the laboratory service tools"]
    result["reaction_outcome"] = "unobserved; obtain a paid measurement"
    return result


def public_receipt(receipt):
    result = copy.deepcopy(receipt)
    # Hashes containing the hidden scenario/seed belong only in replay evidence.
    result.get("result", {}).get("assay", {}).pop("inventory_sha256", None)
    return result


def validate_assessment(probability_success, decision):
    if type(probability_success) not in (int, float) or not math.isfinite(probability_success) or not 0 <= probability_success <= 1:
        raise ValueError("probability_success must be a finite number in 0..1")
    if decision not in ("accept", "investigate", "insufficient_evidence"):
        raise ValueError("decision must be accept, investigate, or insufficient_evidence")


def assess_calibration(assessments, experiments, actions, code_hash, inventory_hash, actual_success):
    """Score only the final current assessment; no reward for repeated guesses."""
    if not assessments or not experiments:
        return {"assessed": False, "reason": "No final assessment or experiment"}
    assessment, experiment = assessments[-1], experiments[-1]
    try:
        validate_assessment(assessment["probability_success"], assessment["decision"])
    except (KeyError, TypeError, ValueError):
        return {"assessed": False, "reason": "Invalid final assessment"}
    if (assessment.get("experiment_id") != experiment["id"]
            or assessment.get("protocol_sha256") != code_hash
            or assessment.get("inventory_sha256") != inventory_hash
            or experiment["protocol_sha256"] != code_hash
            or experiment["inventory_sha256"] != inventory_hash
            or assessment.get("action_count") != len(actions)):
        return {"assessed": False, "reason": "Assessment predates current code, inventory, experiment, or measurement"}
    p = assessment["probability_success"]
    return {"assessed": True, "probability_success": p, "actual_success": bool(actual_success),
            "brier_score": (p - int(bool(actual_success))) ** 2,
            "decision": assessment["decision"], "experiment_id": experiment["id"]}
