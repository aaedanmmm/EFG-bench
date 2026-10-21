"""Independent SDK check of reviewed protocol files, including constructed examples.

This executes Python via Opentrons' standard simulator. Use only on protocols you
have reviewed and trust. The agent-facing environment never uses this path.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
from opentrons.simulate import format_runlog, simulate

parser = argparse.ArgumentParser()
parser.add_argument("protocols", type=Path, nargs="+")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
record = {
    "command": ["python", "results/check_native.py", *[str(p) for p in args.protocols], "--output", str(args.output)],
    "engine": "opentrons.simulate.simulate (native Python execution of reviewed code)",
    "opentrons": importlib.metadata.version("opentrons"),
    "scope": "Virtual robot command acceptance only; mixture correctness is checked separately by src.validate",
    "protocols": [],
}
for path in args.protocols:
    entry = {"protocol": str(path), "constructed_example": path.parts[0] == "examples"}
    try:
        with path.open() as stream:
            runlog, _ = simulate(stream)
        entry.update(passed=True, runlog=format_runlog(runlog))
    except Exception as exc:
        entry.update(passed=False, error=f"{type(exc).__name__}: {exc}")
    record["protocols"].append(entry)
args.output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"passed": all(p["passed"] for p in record["protocols"]), "protocol_count": len(record["protocols"])}))
raise SystemExit(0 if all(p["passed"] for p in record["protocols"]) else 1)
