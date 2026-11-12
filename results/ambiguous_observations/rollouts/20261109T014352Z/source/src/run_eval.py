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
from src.model_policy import require_openrouter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model", default="openrouter/moonshotai/kimi-k3")
    parser.add_argument("--judge-model", help="Optional separate model-based contamination-response judge")
    parser.add_argument("--judge-max-tokens", type=int, default=8000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--suite", choices=["mixing", "ordering", "biochemistry", "biochemistry_ordering", "failures", "gene_design"], default="mixing")
    parser.add_argument("--design-config", type=Path, help="Custom gene design target and constraints in JSON")
    parser.add_argument("--observation-mode", choices=["deterministic", "ambiguous"], default="deterministic",
                        help="Optional abstract uncertain observations for the failures suite")
    parser.add_argument("--observation-seed", type=int, default=0, help="Private reproducible observation seed, recorded in results")
    parser.add_argument("--message-limit", type=int, help="Defaults: mixing 30, biochemistry 40, failures 90, other suites 60")
    parser.add_argument("--max-tokens", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=Path("results/rollouts"))
    args = parser.parse_args()
    try:
        require_openrouter(args.model)
        if args.judge_model is not None:
            require_openrouter(args.judge_model)
    except ValueError as exc:
        parser.error(str(exc))
    if args.message_limit is None:
        args.message_limit = {"mixing": 30, "biochemistry": 40, "failures": 90}.get(args.suite, 60)
    if args.suite == "gene_design" and args.judge_model:
        parser.error("--judge-model applies to the OT-2 suites")
    if args.design_config and args.suite != "gene_design":
        parser.error("--design-config requires --suite gene_design")
    if args.observation_mode == "ambiguous" and args.suite != "failures":
        parser.error("--observation-mode ambiguous requires --suite failures")
    if not 0 <= args.observation_seed < 2**63:
        parser.error("--observation-seed must be in 0..2**63-1")
    if args.observation_mode == "ambiguous" and args.judge_model:
        parser.error("The existing contamination judge is not calibrated for ambiguous observations; use the separate outcome and Brier reports")
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    if not os.environ.get("OPENROUTER_API_KEY") and os.environ.get("OPEN-ROUTER_API"):
        os.environ["OPENROUTER_API_KEY"] = os.environ["OPEN-ROUTER_API"]
    from inspect_ai import eval
    from src.scenarios import ROOT
    if args.suite == "gene_design":
        from src.design_task import gene_design
        evaluation = gene_design(
            message_limit=args.message_limit,
            scenario_file=str(args.design_config) if args.design_config else None,
        )
        environment = "sample-scoped simulated gene design lab; no physical execution or purchases"
    else:
        ot2_mixing = importlib.import_module("src.abc-2").ot2_mixing
        evaluation = ot2_mixing(message_limit=args.message_limit, suite=args.suite, judge_model=args.judge_model, judge_max_tokens=args.judge_max_tokens,
                               observation_mode=args.observation_mode, observation_seed=args.observation_seed)
        environment = "sample-scoped capability tools; bounded interpreter; separate simulator subprocess per call; no Docker needed"
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
        "environment": environment,
        "command": ["python", "-m", "src.run_eval", "--model", args.model, "--suite", args.suite, "--message-limit", str(args.message_limit), "--max-tokens", str(args.max_tokens)] + (["--limit", str(args.limit)] if args.limit else []) + ["--output", str(args.output)] + (["--judge-model", args.judge_model, "--judge-max-tokens", str(args.judge_max_tokens)] if args.judge_model else []),
        "credential_source": "local environment or --env-file (not recorded)",
    }
    if args.design_config:
        record["configuration"]["design_config_sha256"] = hashlib.sha256(args.design_config.read_bytes()).hexdigest()
        record["command"].extend(["--design-config", str(args.design_config)])
    if args.observation_mode == "ambiguous":
        from src.observations import VERSION
        record["configuration"].update(observation_mode=args.observation_mode, observation_model=VERSION,
                                       observation_seed=args.observation_seed)
        record["command"].extend(["--observation-mode", args.observation_mode, "--observation-seed", str(args.observation_seed)])
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    logs = eval(
        evaluation, model=args.model,
        limit=args.limit, log_dir=str(directory), max_tokens=args.max_tokens,
        temperature=0, max_samples=1, max_connections=1, max_retries=1,
    )
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    record["evaluations"] = []
    observation_results = []
    for log in logs:
        record["evaluations"].append({"status": log.status, "log": log.location, "results": log.results.model_dump(mode="json") if log.results else None})
        for sample in log.samples or []:
            evidence = {"sample_id": sample.id, "epoch": sample.epoch, "scores": {name: score.model_dump(mode="json") for name, score in (sample.scores or {}).items()}}
            prefix = directory / str(sample.id)
            prefix.with_suffix(".json").write_text(json.dumps(evidence, indent=2) + "\n")
            for score in (sample.scores or {}).values():
                if score.metadata and score.metadata.get("observation_model"):
                    observation_results.append(score.metadata)
                if score.metadata and "protocol_source" in score.metadata:
                    prefix.with_suffix(".py").write_text(score.metadata["protocol_source"])
                    if score.metadata.get("biochemistry", {}).get("applicable"):
                        from src.review import write_review
                        write_review(score.metadata, directory / (str(sample.id) + "_review"), origin="actual Inspect rollout: " + args.model)
    if args.observation_mode == "ambiguous":
        assessed = [result["calibration"] for result in observation_results if result.get("calibration", {}).get("assessed")]
        record["observation_summary"] = {
            "samples": sum(len(log.samples or []) for log in logs),
            "actual_successes": sum(bool(result.get("actual_success")) for result in observation_results),
            "completed_tasks": sum(bool(result.get("passed")) for result in observation_results),
            "assessed_samples": len(assessed),
            "mean_brier_score": sum(result["brier_score"] for result in assessed) / len(assessed) if assessed else None,
            "note": "Brier score is lower-is-better and conditional on assessment coverage. Constructed observation probabilities are not wet-lab validation.",
        }
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Run record and artifacts: {directory}")
    return 0 if logs and all(log.status == "success" for log in logs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
