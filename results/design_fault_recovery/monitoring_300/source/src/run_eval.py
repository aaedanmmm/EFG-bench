"""Reproducible run wrapper; credentials are loaded but never included in records."""
import argparse
from decimal import Decimal, InvalidOperation
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
    parser.add_argument("--sample-id", action="append", help="Run only this sample ID; repeat to select multiple")
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--min-request-interval", type=float, default=0, help="Minimum seconds between shared budgeted requests")
    parser.add_argument("--suite", choices=["mixing", "ordering", "biochemistry", "biochemistry_ordering", "failures", "gene_design", "design_fault_recovery"], default="mixing")
    parser.add_argument("--recovery-seed", type=int, default=0, help="Private task assignment seed for design_fault_recovery")
    parser.add_argument("--design-config", type=Path, help="Custom gene design target and constraints in JSON")
    parser.add_argument("--observation-mode", choices=["deterministic", "ambiguous"], default="deterministic",
                        help="Optional abstract uncertain observations for the failures suite")
    parser.add_argument("--observation-seed", type=int, default=0, help="Private reproducible observation seed, recorded in results")
    limits = parser.add_mutually_exclusive_group()
    limits.add_argument("--message-limit", type=int, help="Defaults: mixing 30, biochemistry 40, failures 90, other suites 60")
    limits.add_argument("--no-message-limit", action="store_true")
    parser.add_argument("--budget-usd", type=Decimal, help="Shared OpenRouter Kimi K3 inference ceiling in USD")
    parser.add_argument("--budget-ledger", type=Path, help="SQLite path shared by every suite in a budgeted run")
    parser.add_argument("--max-tokens", type=int, default=5000)
    parser.add_argument("--output", type=Path, default=Path("results/rollouts"))
    args = parser.parse_args()
    try:
        require_openrouter(args.model)
        if args.judge_model is not None:
            require_openrouter(args.judge_model)
    except ValueError as exc:
        parser.error(str(exc))
    if (args.budget_usd is None) != (args.budget_ledger is None):
        parser.error("--budget-usd and --budget-ledger must be supplied together")
    if args.max_retries < 0:
        parser.error("--max-retries must be nonnegative")
    if not 0 <= args.min_request_interval <= 60 or (args.min_request_interval and args.budget_usd is None):
        parser.error("--min-request-interval must be in 0..60 and requires a budget when nonzero")
    if args.limit is not None and args.sample_id:
        parser.error("--limit and --sample-id are mutually exclusive")
    if args.no_message_limit and args.budget_usd is None:
        parser.error("--no-message-limit requires a shared inference budget")
    if args.budget_usd is not None:
        from src.openrouter_budget import MODEL
        if args.model != MODEL or args.judge_model:
            parser.error("The budget guard supports Kimi K3 as the only model")
        if not args.budget_usd.is_finite() or args.budget_usd <= 0:
            parser.error("--budget-usd must be a finite positive amount")
        if not 0 < args.max_tokens <= 5000:
            parser.error("Budgeted runs require --max-tokens in 1..5000")
    if args.message_limit is None and not args.no_message_limit:
        args.message_limit = {"mixing": 30, "biochemistry": 40, "failures": 90, "design_fault_recovery": 90}.get(args.suite, 60)
    if not 0 <= args.recovery_seed < 2**63:
        parser.error("--recovery-seed must be in 0..2**63-1")
    if args.recovery_seed and args.suite != "design_fault_recovery":
        parser.error("--recovery-seed requires --suite design_fault_recovery")
    if args.suite in ("gene_design", "design_fault_recovery") and args.judge_model:
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
    if args.suite == "design_fault_recovery":
        from src.design_task import design_fault_recovery
        evaluation = design_fault_recovery(message_limit=args.message_limit, seed=args.recovery_seed)
        environment = "sample-scoped simulated design and fault recovery lab; no OT-2 or physical execution"
    elif args.suite == "gene_design":
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
        "configuration": {"judge_model": args.judge_model, "judge_max_tokens": args.judge_max_tokens, "suite": args.suite, "limit": args.limit, "message_limit": args.message_limit, "max_tokens": args.max_tokens, "temperature": 0, "max_samples": 1, "max_connections": 1, "max_retries": args.max_retries},
        "python": platform.python_version(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("inspect-ai", "opentrons", "openai", "biopython")},
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for pattern in ("src/*.py", "data/*.json", "data/**/*.fasta", "requirements*.txt") for path in sorted(ROOT.glob(pattern))},
        "environment": environment,
        "command": ["python", "-m", "src.run_eval", "--model", args.model, "--suite", args.suite, "--message-limit", str(args.message_limit), "--max-tokens", str(args.max_tokens)] + (["--limit", str(args.limit)] if args.limit else []) + ["--output", str(args.output)] + (["--judge-model", args.judge_model, "--judge-max-tokens", str(args.judge_max_tokens)] if args.judge_model else []),
        "credential_source": "local environment or --env-file (not recorded)",
    }
    if args.suite == "design_fault_recovery":
        record["configuration"]["recovery_seed"] = args.recovery_seed
        record["command"].extend(["--recovery-seed", str(args.recovery_seed)])
    if args.design_config:
        record["configuration"]["design_config_sha256"] = hashlib.sha256(args.design_config.read_bytes()).hexdigest()
        record["command"].extend(["--design-config", str(args.design_config)])
    if args.observation_mode == "ambiguous":
        from src.observations import VERSION
        record["configuration"].update(observation_mode=args.observation_mode, observation_model=VERSION,
                                       observation_seed=args.observation_seed)
        record["command"].extend(["--observation-mode", args.observation_mode, "--observation-seed", str(args.observation_seed)])
    model = args.model
    if args.sample_id:
        record["configuration"]["sample_ids"] = args.sample_id
        for sample_id in args.sample_id:
            record["command"].extend(["--sample-id", sample_id])
    if args.max_retries != 1:
        record["command"].extend(["--max-retries", str(args.max_retries)])
    if args.no_message_limit:
        index = record["command"].index("--message-limit")
        record["command"][index:index + 2] = ["--no-message-limit"]
    if args.budget_usd is not None:
        from src.openrouter_budget import BudgetLedger, PRICE_PER_MILLION, ROUTES, budgeted_model
        ledger_path = ROOT / args.budget_ledger
        try:
            ledger = BudgetLedger(ledger_path, args.budget_usd, args.min_request_interval)
        except (InvalidOperation, ValueError) as exc:
            parser.error(str(exc))
        model = budgeted_model(ledger, args.max_tokens)
        record["configuration"].update(
            budget_usd=str(args.budget_usd), budget_ledger=str(args.budget_ledger),
            routing_price_caps=PRICE_PER_MILLION, allowed_routes=ROUTES,
            min_request_interval=args.min_request_interval,
        )
        record["command"].extend([
            "--budget-usd", str(args.budget_usd), "--budget-ledger", str(args.budget_ledger),
        ])
        if args.min_request_interval:
            record["command"].extend(["--min-request-interval", str(args.min_request_interval)])
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    logs = eval(
        evaluation, model=model,
        limit=args.limit, sample_id=args.sample_id, log_dir=str(directory), max_tokens=args.max_tokens,
        temperature=0, max_samples=1, max_connections=1, max_retries=args.max_retries,
        log_model_api=True if args.budget_usd is not None else None,
        fail_on_error=False if args.budget_usd is not None else None,
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
