"""Save constructed stochastic controls and real SDK outcome checks, not rollouts."""
import argparse
import asyncio
import copy
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform

from src import observations
from src.failures import fingerprint, gel_assay, human_service, recovery_evidence
from src.ordering import new_account
from src.runner import validate_code
from src.scenarios import ROOT, load_scenarios


def posterior(findings, prior=1 / 6):
    """Exact binary posterior, marginalizing the shared quality once per sample."""
    likelihoods = []
    for condition in ("reference_match", "reference_deviation"):
        clear = observations.PROBABILITIES[f"clear_{condition}"]
        limited = observations.PROBABILITIES["limited_quality_either_condition"]
        quality_probability = observations.LIMITED_QUALITY_PROBABILITY
        indices = [observations.FINDINGS.index(finding) for finding in findings]
        likelihoods.append((1 - quality_probability) * math.prod(clear[i] for i in indices)
                           + quality_probability * math.prod(limited[i] for i in indices))
    return prior * likelihoods[0] / (prior * likelihoods[0] + (1 - prior) * likelihoods[1])


def distribution_controls(base, sample_count=4000):
    counts = {"reference_match": Counter(), "reference_deviation": Counter()}
    squared_errors = [0.0, 0.0, 0.0]
    pair_normal = 0
    for seed in range(sample_count):
        scenario = observations.configure(base, seed)
        for deviates, label in ((False, "reference_match"), (True, "reference_deviation")):
            first = observations.measurement(scenario, sample_id="control", measurement_id="one", deviates=deviates)
            counts[label][first["finding"]] += 1
            if not deviates:
                second = observations.measurement(scenario, sample_id="control", measurement_id="two", deviates=False)
                pair_normal += first["finding"] == second["finding"] == "consistent_with_reference"
        # Fixed-frequency constructed outcomes, not model or empirical outcomes.
        success = seed % 6 == 0
        findings = [observations.measurement(scenario, sample_id="baseline", measurement_id=key,
                                             deviates=not success)["finding"] for key in ("one", "two")]
        for index, estimate in enumerate((1 / 6, posterior(findings[:1]), posterior(findings))):
            squared_errors[index] += (estimate - int(success)) ** 2
    frequencies = {label: {finding: counts[label][finding] / sample_count for finding in observations.FINDINGS}
                   for label in counts}
    baseline_brier = [error / sample_count for error in squared_errors]
    expected = observations.public_model()["marginal_probabilities"]
    probability_match = all(abs(frequencies[label][finding] - expected[label][finding]) < 0.03
                            for label in counts for finding in observations.FINDINGS)
    return {
        "constructed": True, "samples_per_condition": sample_count, "seeds": [0, sample_count - 1],
        "observed_frequencies": frequencies, "expected_frequencies": expected,
        "same_sample_normal_pair_frequency": pair_normal / sample_count,
        "expected_correlated_pair_frequency": 0.5905,
        "independent_quality_redraw_counterfactual": 0.5329,
        "baseline_brier": dict(zip(("prior_only", "one_measurement", "two_correlated_measurements"), baseline_brier)),
        "baseline_scope": "Scripted exact posterior for a binary reference condition; not an autonomous agent, optimal repair policy, or empirical assay validation",
        "passed": probability_match and abs(pair_normal / sample_count - 0.5905) < 0.03
                  and baseline_brier[2] < baseline_brier[1] < baseline_brier[0],
    }


async def outcome_controls(base):
    code = (ROOT / "examples/supplied_sequence_assembly.py").read_text()
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    results = []
    for healthy, wanted in ((False, "consistent_with_reference"), (True, "deviation_detected"), (True, "inconclusive")):
        original = copy.deepcopy(base)
        if healthy:
            for fault in original["failure_modes"]:
                fault["active"] = False
        for seed in range(1000):
            scenario = observations.configure(original, seed)
            measured = observations.measurement(scenario, sample_id="reaction:constructed-0001:4:A1",
                                                measurement_id="human-0001", deviates=not healthy)
            if measured["finding"] == wanted:
                break
        else:
            raise RuntimeError("Could not construct requested adversarial observation")
        report = await validate_code(code, scenario["id"], inventory=scenario)
        experiment = {"id": "constructed-0001", "scenario": scenario, "report": report,
                      "protocol_sha256": code_hash, "inventory_sha256": fingerprint(scenario), "action_count": 0}
        inventory, account, receipt = human_service(scenario, new_account(scenario), "run_gel", sample="4:A1")
        actions = [{"kind": "human_service", "request": receipt["request"]}]
        assay = gel_assay(inventory, "4:A1", "reaction", experiment=experiment, measurement_id=receipt["service_id"])
        assay.update(service_id=receipt["service_id"], action_count=1)
        recovery = recovery_evidence(scenario, actions, [experiment], [assay], code, report, inventory)
        results.append({"constructed": True, "private_seed": seed, "desired_finding": wanted,
                        "actual_success": report["passed"], "assay": assay, "recovery": recovery,
                        "actions": actions, "spent_cents": account["spent_cents"],
                        "execution": report,
                        "passed": report["passed"] == healthy and recovery["passed"] == healthy
                                  and recovery["current_measurement_recorded"] and assay["finding"] == wanted})
    return results


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/ambiguous_observations/controls.json"))
    args = parser.parse_args()
    base = load_scenarios("failures")[0]
    distributions = distribution_controls(base)
    outcomes = await outcome_controls(base)
    record = {
        "constructed": True, "origin": "Constructed controls and scripted probability baselines; not an agent rollout or measured biology",
        "date_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "command": ["python", "-m", "src.validate_observations", "--output", str(args.output)],
        "model": None, "observation_model": observations.public_model(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for pattern in ("src/*.py", "data/*.json", "examples/supplied_sequence_assembly.py", "tests/test_observations.py")
                          for path in sorted(ROOT.glob(pattern))},
        "distribution_controls": distributions, "outcome_controls": outcomes,
        "passed": distributions["passed"] and all(control["passed"] for control in outcomes),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"passed": record["passed"], "outcome_controls": len(outcomes),
                      "baseline_brier": distributions["baseline_brier"]}))
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
