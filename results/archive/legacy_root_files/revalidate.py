"""Replay saved model artifacts exclusively through the bounded runtime."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

# Enable `python results/archive/legacy_root_files/revalidate.py ...` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.runner import validate_code
from src.scenarios import ROOT, get_scenario
from src.ordering import replay_orders, account_summary


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {
        "command": ["python", "results/archive/legacy_root_files/revalidate.py", str(args.directory), "--output", str(args.output)],
        "scope": "Actual saved model artifacts revalidated by the bounded interpreter; no new model generation",
        "python": platform.python_version(),
        "opentrons": importlib.metadata.version("opentrons"),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for pattern in ("src/*.py", "data/*.json", "requirements*.txt") for path in sorted(ROOT.glob(pattern))},
        "protocols": [],
    }
    for path in sorted(args.directory.glob("*.py")):
        scenario = get_scenario(path.stem)
        if scenario.get("ordering"):
            evidence = json.loads(path.with_suffix(".json").read_text())
            metadata = next(score["metadata"] for score in evidence["scores"].values() if score.get("metadata", {}).get("ordering"))
            inventory, account = replay_orders(scenario, metadata["ordering"]["orders"])
            report = await validate_code(path.read_text(), path.stem, inventory=inventory)
            report["ordering"] = account_summary(account)
        else:
            report = await validate_code(path.read_text(), path.stem)
        record["protocols"].append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "validation": report})
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    passed = bool(record["protocols"]) and all(p["validation"]["passed"] for p in record["protocols"])
    print(json.dumps({"passed": passed, "protocol_count": len(record["protocols"])}))
    return 0 if passed else 1


raise SystemExit(asyncio.run(main()))
