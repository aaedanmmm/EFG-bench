"""Summarize artifact scores, timings, and OpenRouter-reported inference charges."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from statistics import median
from pathlib import Path

from inspect_ai.log import read_eval_log
from inspect_ai.scorer import CORRECT

ROOT = Path(__file__).resolve().parent
SUITES = (
    "mixing", "ordering", "biochemistry", "biochemistry_ordering",
    "failures", "failures_ambiguous", "gene_design",
)
MODEL = "openrouter/moonshotai/kimi-k3"


def summarize_sample(sample, billing):
    calls = [
        event.call.response for event in sample.events
        if event.event == "model" and event.model == MODEL and event.call
        and event.call.response and event.call.response.get("id")
    ]
    # Count a generation ID once if Inspect repeats it in the event stream.
    responses = {response["id"]: response for response in calls}
    generation_ids = sorted({
        event.output.response_id for event in sample.events
        if event.event == "model" and event.model == MODEL and event.output
        and event.output.response_id
    } | responses.keys())
    costs = [
        billing.get(generation_id, {}).get(
            "total_cost", (responses.get(generation_id, {}).get("usage") or {}).get("cost")
        )
        for generation_id in generation_ids
    ]
    providers = {
        billing.get(generation_id, {}).get("provider_name")
        or responses.get(generation_id, {}).get("provider")
        for generation_id in generation_ids
    }
    score = next(iter((sample.scores or {}).values()), None)
    usage = sample.model_usage.get(MODEL) if sample.model_usage else None
    metadata = score.metadata or {} if score else {}
    ordering = metadata.get("ordering") or {}
    calibration = metadata.get("calibration") or {}
    provider_times = [
        billing[generation_id]["latency"] for generation_id in generation_ids
        if billing.get(generation_id, {}).get("latency") is not None
    ]
    return {
        "id": sample.id,
        "correct": score.value == CORRECT if score else None,
        "score_explanation": score.explanation if score else None,
        "seconds": sample.total_time,
        "simulated_spend_cents": metadata.get("spent_cents", ordering.get("spent_cents")),
        "actual_simulated_success": metadata.get("actual_success"),
        "brier_score": calibration.get("brier_score"),
        "provider_latencies_ms": provider_times,
        "limit": sample.limit.model_dump(mode="json") if sample.limit else None,
        "error": sample.error.message if sample.error else None,
        "usage": usage.model_dump(mode="json") if usage else None,
        "generation_ids": generation_ids,
        "generations": len(generation_ids),
        "generations_with_reported_cost": sum(cost is not None for cost in costs),
        "reported_cost_usd": str(sum(
            (Decimal(str(cost)) for cost in costs if cost is not None), Decimal(0)
        )),
        "providers": sorted(providers - {None}),
    }


def aggregate(samples):
    usage_fields = ("input_tokens", "input_tokens_cache_read", "input_tokens_cache_write",
                    "output_tokens", "reasoning_tokens", "total_tokens")
    latencies = [value for sample in samples for value in sample["provider_latencies_ms"]]
    return {
        "correct": sum(sample["correct"] is True for sample in samples),
        "scored_samples": sum(sample["correct"] is not None for sample in samples),
        "reported_cost_usd": str(sum(
            (Decimal(sample["reported_cost_usd"]) for sample in samples), Decimal(0)
        )),
        "generations": sum(sample["generations"] for sample in samples),
        "generations_with_reported_cost": sum(sample["generations_with_reported_cost"] for sample in samples),
        "usage": {
            field: sum((sample["usage"] or {}).get(field) or 0 for sample in samples)
            for field in usage_fields
        },
        "median_provider_latency_ms": median(latencies) if latencies else None,
        "sample_seconds": round(sum(sample["seconds"] or 0 for sample in samples), 3),
    }


def main():
    billing_file = ROOT / "generation_billing.json"
    billing = json.loads(billing_file.read_text()) if billing_file.exists() else {}
    suites = {}
    all_attempts = []
    for suite in SUITES:
        paths = sorted((ROOT / suite).glob("*/*.eval"))
        if not paths:
            continue
        runs = []
        attempts = []
        selected = {}
        for path in paths:
            log = read_eval_log(path)
            relative_path = str(path.relative_to(ROOT))
            runs.append({
                "log": relative_path, "status": log.status,
                "configured_samples": log.eval.dataset.samples,
                "started_at": log.stats.started_at, "completed_at": log.stats.completed_at,
            })
            for sample in log.samples or []:
                attempt = {"log": relative_path, **summarize_sample(sample, billing)}
                attempts.append(attempt)
                current = selected.get(sample.id)
                if current is None or current["correct"] is None or attempt["correct"] is not None:
                    selected[sample.id] = attempt
        samples = list(selected.values())
        all_attempts.extend(attempts)
        complete = all(run["completed_at"] for run in runs)
        assessments = [sample["brier_score"] for sample in samples if sample["brier_score"] is not None]
        suites[suite] = {
            "status": ("success" if all(run["status"] == "success" for run in runs) else "error")
                      if complete else "started",
            "configured_samples": runs[0]["configured_samples"],
            "completed_samples": len(samples),
            **aggregate(attempts),
            "correct": sum(sample["correct"] is True for sample in samples),
            "scored_samples": sum(sample["correct"] is not None for sample in samples),
            "started_at": runs[0]["started_at"],
            "completed_at": max(run["completed_at"] for run in runs) if complete else None,
            "mean_brier_score": sum(assessments) / len(assessments) if assessments else None,
            "assessed_samples": len(assessments),
            "runs": runs,
            "samples": samples,
            "attempts": attempts,
        }
    samples = [sample for suite in suites.values() for sample in suite["samples"]]
    with closing(sqlite3.connect(f"file:{ROOT / 'budget.sqlite'}?mode=ro", uri=True)) as database:
        ceiling, = database.execute("SELECT amount FROM budget").fetchone()
        charged, unknown, pending, calls = database.execute("""
            SELECT COALESCE(SUM(charged), 0),
                   COALESCE(SUM(CASE WHEN in_flight = 0 AND charged IS NULL THEN reserved END), 0),
                   COALESCE(SUM(CASE WHEN in_flight = 1 THEN reserved END), 0),
                   COUNT(*)
            FROM calls
        """).fetchone()
    ledger = {label: str(Decimal(value) / 10**12) for label, value in (
        ("ceiling_usd", ceiling), ("settled_usd", charged),
        ("unconfirmed_reserve_usd", unknown), ("in_flight_reserve_usd", pending),
    )}
    ledger["requests_dispatched"] = calls
    run_start = min((suite["started_at"] for suite in suites.values() if suite["started_at"]), default=None)
    run_end = (
        max(suite["completed_at"] for suite in suites.values())
        if len(suites) == len(SUITES) and all(suite["completed_at"] for suite in suites.values())
        else None
    )
    summary = {
        "model": MODEL,
        "wall_clock_seconds": (
            (datetime.fromisoformat(run_end) - datetime.fromisoformat(run_start)).total_seconds()
            if run_start and run_end else None
        ),
        "cost_method": "OpenRouter generation total_cost or the recorded response usage.cost when generation billing is unavailable.",
        **aggregate(all_attempts),
        "correct": sum(sample["correct"] is True for sample in samples),
        "scored_samples": sum(sample["correct"] is not None for sample in samples),
        "configured_samples": sum(suite["configured_samples"] for suite in suites.values()),
        "budget_ledger": ledger,
        "suites": suites,
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
