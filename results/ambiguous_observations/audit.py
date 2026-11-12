"""Reproduce the local evidence audit; credentials are compared, never printed."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import xml.etree.ElementTree as ET

from dotenv import dotenv_values
from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
RUN = OUTPUT / "rollouts/20261109T014352Z"
record = json.loads((RUN / "run.json").read_text())
snapshot_mismatches, source_changes = [], []
for name, expected in record["source_sha256"].items():
    if hashlib.sha256((RUN / "source" / name).read_bytes()).hexdigest() != expected:
        snapshot_mismatches.append(name)
    if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
        source_changes.append(name)

credential_values = []
local = dotenv_values(ROOT / ".env") if (ROOT / ".env").exists() else {}
for key in ("OPENROUTER_API_KEY", "OPEN-ROUTER_API"):
    for value in (local.get(key), os.environ.get(key)):
        if value and len(value) >= 8:
            credential_values.append(value.encode())

credential_matches = []
scanned = 0
paths = list(OUTPUT.rglob("*")) + list((ROOT / "src").glob("*.py"))
for path in paths:
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    payload = path.read_bytes()
    if path.suffix == ".eval":
        payload += read_eval_log(path).model_dump_json().encode()
    scanned += 1
    if any(value in payload for value in credential_values):
        credential_matches.append(str(path.relative_to(ROOT)))

tests = {}
for name in ("tests.xml", "focused_tests.xml", "final_focused_tests.xml", "replay_test.xml"):
    suites = ET.parse(OUTPUT / name).getroot().iter("testsuite")
    totals = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.get(key, 0))
    tests[name] = totals
replay = json.loads((OUTPUT / "replay.json").read_text())
controls = json.loads((OUTPUT / "controls.json").read_text())
validation = {
    "date_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
    "audit_command": "python results/ambiguous_observations/audit.py",
    "validation_commands": [
        "python -m pytest -q tests --junitxml=results/ambiguous_observations/tests.xml",
        "python -m pytest -q tests/test_observations.py tests/test_failures.py --junitxml=results/ambiguous_observations/final_focused_tests.xml",
        "python -m pytest -q tests/test_observations.py::test_receipts_replay_idempotency_and_no_private_hashes --junitxml=results/ambiguous_observations/replay_test.xml",
        "python -m src.validate_observations --output results/ambiguous_observations/controls.json",
        "python -m src.replay_failures " + str(next(RUN.glob('*.eval')).relative_to(ROOT)) + " --output results/ambiguous_observations/replay.json",
    ],
    "tests": tests, "constructed_controls_passed": controls["passed"],
    "actual_rollout_model": record["model"], "actual_rollout_summary": record["observation_summary"],
    "actual_rollout_replay_passed": replay["passed"],
    "run_start_snapshot_mismatches": snapshot_mismatches,
    "source_changes_since_run_start": source_changes,
    "source_change_explanation": "Final latest-experiment verification tightening and expanded observation replay; recorded actor already measured its latest experiment and final replay matches.",
    "credential_scan": {"available_credential_values_checked": bool(credential_values),
                        "files_scanned_including_decoded_eval_logs": scanned,
                        "matching_files": credential_matches},
    "current_source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for pattern in ("src/*.py", "tests/test_observations.py", "requirements*.txt")
                              for path in sorted(ROOT.glob(pattern))},
}
validation["passed"] = (not snapshot_mismatches and not credential_matches and controls["passed"] and replay["passed"]
                        and all(not item["failures"] and not item["errors"] for item in tests.values()))
(OUTPUT / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
print(json.dumps({"passed": validation["passed"], "tests": tests,
                  "source_changes_since_run_start": source_changes, "credential_match_count": len(credential_matches)}))
raise SystemExit(0 if validation["passed"] else 1)
