"""Re-run the scorers over the saved artifacts and accepted actions."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from inspect_ai.log import read_eval_log_async
from inspect_ai.scorer import Target
from inspect_ai.util import Store

from src.design_task import gene_design_score
from src.scorer import ot2_mixture

ROOT = Path(__file__).resolve().parent


async def main():
    summary = json.loads((ROOT / "summary.json").read_text())
    results = {}
    for suite, entry in summary["suites"].items():
        if entry["status"] != "success":
            continue
        scorer = gene_design_score() if suite == "gene_design" else ot2_mixture()
        outcomes = []
        logs = {}
        for selected in entry["samples"]:
            if selected["correct"] is None:
                continue
            log_path = selected["log"]
            if log_path not in logs:
                logs[log_path] = await read_eval_log_async(ROOT / log_path)
            sample = next(sample for sample in logs[log_path].samples if sample.id == selected["id"])
            state = SimpleNamespace(metadata=sample.metadata, store=Store(sample.store))
            original = next(iter(sample.scores.values()))
            replayed = await scorer(state, Target(""))
            outcomes.append({
                "id": sample.id,
                "original": original.value,
                "replayed": replayed.value,
                "matched": original.value == replayed.value,
            })
        results[suite] = outcomes
    (ROOT / "score_replay.json").write_text(json.dumps(results, indent=2) + "\n")
    outcomes = [outcome for suite in results.values() for outcome in suite]
    matched = sum(outcome["matched"] for outcome in outcomes)
    print(f"Reproduced {matched}/{len(outcomes)} saved scores.")
    return int(matched != len(outcomes))


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
