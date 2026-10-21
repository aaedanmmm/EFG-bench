"""Judge saved Inspect messages without rerunning the actor or changing its log."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from inspect_ai.log import read_eval_log
from src.judge import Assessment, DEFAULT_JUDGE_MODEL, RUBRIC, RUBRIC_VERSION, assess_timeline, build_timeline
from src.scenarios import ROOT


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--sample-id", action="append", help="Repeat to select samples; default is every saved sample")
    parser.add_argument("--max-tokens", type=int, default=8000)
    parser.add_argument("--output", type=Path, default=Path("results/judge"))
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    if not os.environ.get("OPENROUTER_API_KEY") and os.environ.get("OPEN-ROUTER_API"):
        os.environ["OPENROUTER_API_KEY"] = os.environ["OPEN-ROUTER_API"]
    log = read_eval_log(str(args.log))
    samples = [sample for sample in log.samples or [] if args.sample_id is None or str(sample.id) in args.sample_id]
    if not samples:
        parser.error("No matching saved samples")
    directory = args.output / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "rubric.txt").write_text(RUBRIC + "\n")
    (directory / "schema.json").write_text(json.dumps(Assessment.model_json_schema(), indent=2) + "\n")
    record = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-m", "src.judge_rollout", str(args.log), "--model", args.model, "--max-tokens", str(args.max_tokens), "--output", str(args.output)] + [part for identifier in args.sample_id or [] for part in ("--sample-id", identifier)],
        "credential_source": "local environment or --env-file, contents never recorded",
        "judge_model": args.model, "actor_model": log.eval.model,
        "source_log": str(args.log), "source_log_sha256": hashlib.sha256(args.log.read_bytes()).hexdigest(),
        "source_run_status": log.status,
        "rubric_version": RUBRIC_VERSION,
        "dependencies": {name: importlib.metadata.version(name) for name in ("inspect-ai", "openai", "pydantic")},
        "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "src/judge.py", ROOT / "src/judge_rollout.py")},
        "samples": [],
        "limitations": ["Public transcript behavior, not private cognition or elapsed minutes", "Model judgment is subjective; review cited evidence", "Self-judging when actor and judge model match; configure --model for an independent judge", "An interrupted rollout is partial evidence; the judge must not invent behavior after its end"],
    }
    for index, sample in enumerate(samples, 1):
        path = directory / f"sample-{index:04d}.json"
        events = build_timeline(sample.messages)
        (directory / f"sample-{index:04d}-input.json").write_text(json.dumps(events, indent=2) + "\n")
        (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
        try:
            report = await assess_timeline(events, model=args.model, max_tokens=args.max_tokens)
        except Exception as exc:
            # Provider error strings can contain request details; save the type only.
            report = {"status": "judge_error", "assessment": None, "error": f"Judge request failed: {type(exc).__name__}"}
        report.update(sample_id=sample.id, epoch=sample.epoch, origin="Model judge of actual saved Inspect messages; not a new actor rollout")
        path.write_text(json.dumps(report, indent=2) + "\n")
        record["samples"].append({"sample_id": sample.id, "epoch": sample.epoch,
                                  "path": path.name, "status": report["status"],
                                  "category": (report.get("assessment") or {}).get("category"),
                                  "refused": (report.get("assessment") or {}).get("refused"),
                                  "refusal_scope": (report.get("assessment") or {}).get("refusal_scope")})
        print(json.dumps(record["samples"][-1]), flush=True)
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Judgments: {directory}")
    return 1 if any(sample["status"] == "judge_error" for sample in record["samples"]) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
