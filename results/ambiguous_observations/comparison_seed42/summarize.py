"""Summarize actual paired runs after completion; no new model calls."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values
from inspect_ai.log import read_eval_log

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def summarize(label):
    run_files = list((OUT / label).glob("*/run.json"))
    if len(run_files) != 1:
        raise ValueError(f"Expected exactly one run for {label}")
    run_path = run_files[0]
    record = json.loads(run_path.read_text())
    log_path = next(run_path.parent.glob("*.eval"))
    log = read_eval_log(log_path)
    if log.status != "success" or len(log.samples or []) != 6:
        raise ValueError(f"{label} is not a completed six-sample run")
    replay = json.loads((OUT / f"{label}_replay.json").read_text())
    samples, costs, providers, generation_ids = [], [], Counter(), set()
    cost_missing = 0
    for sample in log.samples:
        grade = sample.scores["ot2_mixture"]
        evidence = grade.metadata or {}
        calibration = evidence.get("calibration", {})
        scenario = sample.metadata["scenario"]
        faults = [f for f in scenario.get("failure_modes", []) if f.get("active", True)]
        condition = "healthy" if not faults else faults[0]["kind"]
        if condition == "temperature_offset":
            condition += "_hot" if faults[0]["offset_c"] > 0 else "_cold"
        sample_costs = []
        for event in sample.events:
            if getattr(event, "event", "") != "model":
                continue
            payload = event.model_dump(mode="json")
            response = (payload.get("call") or {}).get("response") or {}
            if not isinstance(response, dict):
                cost_missing += 1
                continue
            generation_id = response.get("id")
            if generation_id and generation_id in generation_ids:
                continue
            if generation_id:
                generation_ids.add(generation_id)
            providers[response.get("provider", "unreported")] += 1
            cost = (response.get("usage") or {}).get("cost")
            if isinstance(cost, (float, int)):
                sample_costs.append(cost)
                costs.append(cost)
            else:
                cost_missing += 1
        samples.append({
            "sample_id": sample.id, "hidden_condition": condition,
            "overall_correct": grade.value == "C", "actual_success": evidence.get("actual_success"),
            "confidence_assessed": calibration.get("assessed", False),
            "probability_success": calibration.get("probability_success"),
            "brier_score": calibration.get("brier_score"), "decision": calibration.get("decision"),
            "spent_cents": evidence.get("ordering", {}).get("spent_cents"),
            "experiment_count": len(sample.store.get("experiments", [])),
            "paid_sample_measurements": len(sample.store.get("assays", [])),
            "reported_api_cost_usd": sum(sample_costs),
            "explanation": grade.explanation, "error": sample.error.message if sample.error else None,
        })
    hashes_match = all(hashlib.sha256((run_path.parent / "source" / name).read_bytes()).hexdigest() == digest
                       for name, digest in record["source_sha256"].items())
    current_match = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                        for name, digest in record["source_sha256"].items())
    assessed = [sample for sample in samples if sample["confidence_assessed"]]
    return {
        "model": record["model"], "log": str(log_path.relative_to(OUT)),
        "run_record": str(run_path.relative_to(OUT)), "configuration": record["configuration"],
        "samples": samples, "completed_tasks": sum(s["overall_correct"] for s in samples),
        "actual_successes": sum(s["actual_success"] is True for s in samples),
        "assessment_coverage": len(assessed),
        "mean_brier_score": sum(s["brier_score"] for s in assessed) / len(assessed) if assessed else None,
        "mean_simulated_spend_usd": sum(s["spent_cents"] or 0 for s in samples) / 600,
        "reported_api_cost_usd": sum(costs), "generation_costs_missing": cost_missing,
        "provider_generation_counts": dict(providers),
        "model_usage": {k: v.model_dump(mode="json") for k, v in log.stats.model_usage.items()},
        "replay_passed": replay["passed"], "snapshot_hashes_match": hashes_match,
        "current_sources_match": current_match,
    }


models = [summarize(label) for label in ("kimi", "deepseek")]
comparison = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "origin": "Actual OpenRouter agent rollouts; observations and laboratory outcomes are simulated",
    "command": "python results/ambiguous_observations/comparison_seed42/summarize.py",
    "models": models,
    "limits": "One six-case repetition per model. Same observation seed and limits, but adaptive actions can produce different readings. Provider-default reasoning settings; not a compute-matched or statistically conclusive ranking. Costs are API-reported generation charges, excluding credit-purchase fees and taxes.",
}
local = dotenv_values(ROOT / ".env")
secrets = [v.encode() for key in ("OPENROUTER_API_KEY", "OPEN-ROUTER_API")
           for v in (local.get(key), os.environ.get(key)) if v and len(v) >= 8]
matches = []
for path in OUT.rglob("*"):
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    content = path.read_bytes()
    if path.suffix == ".eval":
        content += read_eval_log(path).model_dump_json().encode()
    if any(secret in content for secret in secrets):
        matches.append(str(path.relative_to(OUT)))
comparison["credential_scan"] = {"known_values_checked": bool(secrets), "matching_files": matches}
comparison["validation_passed"] = not matches and all(m["replay_passed"] and m["snapshot_hashes_match"] and m["current_sources_match"] for m in models)
(OUT / "summary.json").write_text(json.dumps(comparison, indent=2) + "\n")
lines = ["# Kimi K3 and DeepSeek V4 Pro: one repetition each", "",
         "Actual OpenRouter runs of the six-case ambiguous-observation suite. Both used observation seed 42, temperature 0, 90 messages, and a 5,000-token output limit per response. No separate model judge was used. The deterministic suite was not run in this comparison.", "",
         "| Model | Tasks correct | Actual simulated success | Assessments | Mean Brier ↓ | Mean lab spend | API-reported cost |",
         "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
for model in models:
    brier = f"{model['mean_brier_score']:.4f}" if model["mean_brier_score"] is not None else "unassessed"
    lines.append(f"| {model['model']} | {model['completed_tasks']}/6 | {model['actual_successes']}/6 | {model['assessment_coverage']}/6 | {brier} | ${model['mean_simulated_spend_usd']:.2f} | US${model['reported_api_cost_usd']:.4f} |")
lines += ["", "Brier scores are conditional on assessment coverage. Laboratory spending is simulated; API charges are real reported generation costs, excluding taxes and credit-purchase fees. See the machine-readable summary for any missing generation costs.", "",
          "## Per-case results", "", "| Condition | Kimi correct | DeepSeek correct | Kimi confidence | DeepSeek confidence |",
          "| --- | --- | --- | ---: | ---: |"]
for kimi, deepseek in zip(models[0]["samples"], models[1]["samples"]):
    if kimi["hidden_condition"] != deepseek["hidden_condition"] or kimi["sample_id"] != deepseek["sample_id"]:
        raise ValueError("Scenario pairing mismatch")
    lines.append(f"| {kimi['hidden_condition']} | {kimi['overall_correct']} | {deepseek['overall_correct']} | {kimi['probability_success']} | {deepseek['probability_success']} |")
lines += ["", "## Evidence", "", "[Summary and validation](summary.json) records per-case scores, usage, provider routing, explanations, source hashes, and credential-scan results. [Configuration](comparison_config.json) records the shared setup and installed versions. [Model metadata](model_metadata.json) preserves the public model IDs and price snapshot; advertised catalogue rates are not used in place of returned generation costs.", ""]
for label, model in zip(("kimi", "deepseek"), models):
    lines.append(f"- {model['model']}: [Inspect log]({model['log']}), [run command and configuration]({model['run_record']}), [independent replay]({label}_replay.json). Source snapshots and generated protocols sit beside each run record.")
lines += ["", "## Interpretation", "", comparison["limits"], "",
          "Replay success means the observations and grades were reproduced; it does not mean the agent solved every task. These runs do not validate biological realism. Preserve this repetition separately from the earlier seed-41 Kimi pilot.", ""]
(OUT / "README.md").write_text("\n".join(lines))
print(json.dumps({"validation_passed": comparison["validation_passed"], "models": [
    {key: model[key] for key in ("model", "completed_tasks", "assessment_coverage", "mean_brier_score", "reported_api_cost_usd", "generation_costs_missing")}
    for model in models]}))
raise SystemExit(0 if comparison["validation_passed"] else 1)
