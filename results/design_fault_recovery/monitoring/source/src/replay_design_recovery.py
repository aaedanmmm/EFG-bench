"""Independently replay completed design + recovery Inspect sample evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from inspect_ai.log import read_eval_log

from src.design_lab import grade_lab
from src.design_recovery import load_recovery_scenarios
from src.scenarios import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_record", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = json.loads(args.run_record.read_text())
    if record["configuration"]["suite"] != "design_fault_recovery":
        raise ValueError("Expected a design_fault_recovery run record")
    scenarios = {s["id"]: s for s in load_recovery_scenarios(record["configuration"]["recovery_seed"])}
    comparisons = []
    for evaluation in record["evaluations"]:
        log = read_eval_log(evaluation["log"])
        for sample in log.samples or []:
            for score in (sample.scores or {}).values():
                saved = score.metadata
                if not saved or "actions" not in saved:
                    continue
                replayed = grade_lab(scenarios[sample.id], saved["actions"])
                expected = {key: value for key, value in saved.items() if key != "actions"}
                comparisons.append({"sample_id": sample.id, "matched": replayed == expected,
                                    "actual_success": replayed["passed"], "replayed": replayed})
    source_mismatches = [name for name, digest in record["source_sha256"].items()
                         if not (ROOT / name).exists() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    output = {"origin": "Independent replay of an actual OpenRouter rollout; all biology is simulated",
              "model": record["model"], "run_record": str(args.run_record),
              "source_mismatches": source_mismatches, "samples": comparisons,
              "passed": bool(comparisons) and all(item["matched"] for item in comparisons) and not source_mismatches}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Replay matched: {output['passed']}; {len(comparisons)} sample(s)")
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
