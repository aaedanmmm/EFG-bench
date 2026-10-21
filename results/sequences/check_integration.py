"""Local sequence and ordering validation. No model calls or external services.

Protocols and order requests here are constructed validation fixtures, not agent
rollouts. The simulator uses actual SDK virtual hardware via the bounded runtime.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.fragments import ordering_scenario, sequence_manifest
from src.ordering import account_summary, new_account, place_order
from src.runner import validate_code
from src.scenarios import ROOT


async def main():
    paths = sorted((ROOT / "data/sequences").glob("*.fasta"))
    before = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    partition = subprocess.run([sys.executable, "src/split_sequence.py"], cwd=ROOT, text=True, capture_output=True)
    if partition.returncode:
        raise RuntimeError(partition.stderr)
    after = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    assert before == after, "Reproducing partitions must preserve exact supplied FASTA bytes"
    manifest = sequence_manifest()
    scenario = ordering_scenario()
    account = new_account(scenario)
    for location, source in scenario["sources"].items():
        component = next(iter(source["components"]))
        item = "nuclease_free_water" if component == "water" else component
        scenario, account, _ = place_order(scenario, account, item, location)
    for item, slot in [("filtered_tips_20ul","2"),("reaction_plate","3")]:
        scenario, account, _ = place_order(scenario, account, item, slot)
    report = await validate_code((ROOT / "examples/sequence_partitions.py").read_text(), scenario["id"], inventory=scenario)
    result = {
        "type": "Actual local validation using constructed order requests/protocol; not an agent rollout or biochemical measurement",
        "command": [".venv/bin/python", "results/sequences/check_integration.py"],
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("biopython","opentrons","inspect-ai")},
        "partition_command": [".venv/bin/python","src/split_sequence.py"],
        "input_fasta_bytes_preserved":before == after,
        "input_file_sha256": before,
        "manifest": manifest,
        "orders":account_summary(account),
        "simulation":report,
        "source_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "src").glob("*.py"))},
        "passed": bool(manifest["exact_reconstruction"] and report["passed"] and before == after),
    }
    output = ROOT / "results/sequences/integration.json"
    output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"passed":result["passed"],"sequence_parts":len(manifest["fragments"]),"source_bp":manifest["source"]["length_bp"],"spent_cents":account["spent_cents"],"tips_used":report["tips_used"]}))
    return 0 if result["passed"] else 1


raise SystemExit(asyncio.run(main()))
