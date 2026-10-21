"""Reproducible run wrapper; credentials are loaded but never included in records."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model", default="openrouter/moonshotai/kimi-k3")
    parser.add_argument("--judge-model", help="Optional separate model-based contamination-response judge")
    parser.add_argument("--judge-max-tokens", type=int, default=8000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--suite", choices=["mixing", "ordering", "biochemistry", "biochemistry_ordering", "failures"], default="mixing")
    parser.add_argument("--message-limit", type=int, help="Default: mixing 30, ordering/biochemistry_ordering 60, biochemistry 40")
    parser.add_argument("--max-tokens", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=Path("results/rollouts"))
    args = parser.parse_args()
    if args.message_limit is None:
        args.message_limit = {"mixing": 30, "ordering": 60, "biochemistry": 40, "biochemistry_ordering": 60, "failures": 90}[args.suite]
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    if not os.environ.get("OPENROUTER_API_KEY") and os.environ.get("OPEN-ROUTER_API"):
        os.environ["OPENROUTER_API_KEY"] = os.environ["OPEN-ROUTER_API"]
    from inspect_ai import eval
    ot2_mixing = importlib.import_module("src.abc-2").ot2_mixing
    from src.scenarios import ROOT
    directory = ROOT / args.output / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory.mkdir(parents=True, exist_ok=False)
    record = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "configuration": {"judge_model": args.judge_model, "judge_max_tokens": args.judge_max_tokens, "suite": args.suite, "limit": args.limit, "message_limit": args.message_limit, "max_tokens": args.max_tokens, "temperature": 0, "max_samples": 1, "max_connections": 1, "max_retries": 1},
        "python": platform.python_version(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("inspect-ai", "opentrons", "openai", "biopython")},
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for pattern in ("src/*.py", "data/*.json", "data/**/*.fasta", "requirements*.txt") for path in sorted(ROOT.glob(pattern))},
        "environment": "sample-scoped capability tools; bounded interpreter; separate simulator subprocess per call; no Docker needed",
        "command": ["python", "-m", "src.run_eval", "--model", args.model, "--suite", args.suite, "--message-limit", str(args.message_limit), "--max-tokens", str(args.max_tokens)] + (["--limit", str(args.limit)] if args.limit else []) + ["--output", str(args.output)] + (["--judge-model", args.judge_model, "--judge-max-tokens", str(args.judge_max_tokens)] if args.judge_model else []),
        "credential_source": "local environment or --env-file (not recorded)",
    }
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    logs = eval(
        ot2_mixing(message_limit=args.message_limit, suite=args.suite, judge_model=args.judge_model, judge_max_tokens=args.judge_max_tokens), model=args.model,
        limit=args.limit, log_dir=str(directory), max_tokens=args.max_tokens,
        temperature=0, max_samples=1, max_connections=1, max_retries=1,
    )
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    record["evaluations"] = []
    for log in logs:
        record["evaluations"].append({"status": log.status, "log": log.location, "results": log.results.model_dump(mode="json") if log.results else None})
        for sample in log.samples or []:
            evidence = {"sample_id": sample.id, "epoch": sample.epoch, "scores": {name: score.model_dump(mode="json") for name, score in (sample.scores or {}).items()}}
            prefix = directory / str(sample.id)
            prefix.with_suffix(".json").write_text(json.dumps(evidence, indent=2) + "\n")
            for score in (sample.scores or {}).values():
                if score.metadata and "protocol_source" in score.metadata:
                    prefix.with_suffix(".py").write_text(score.metadata["protocol_source"])
                    if score.metadata.get("biochemistry", {}).get("applicable"):
                        from src.review import write_review
                        write_review(score.metadata, directory / (str(sample.id) + "_review"), origin="actual Inspect rollout: " + args.model)
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Run record and artifacts: {directory}")
    return 0 if logs and all(log.status == "success" for log in logs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
