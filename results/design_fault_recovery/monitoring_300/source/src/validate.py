"""Run only in a subprocess: virtual hardware and logs are per-protocol."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--scenario", default="two_reagent_mix")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--inventory", type=Path, help="Trusted ordered inventory snapshot; not exposed to protocol code")
    args = parser.parse_args()
    from src.scenarios import get_scenario
    # Keep SDK diagnostics separate from the machine-readable result.
    with contextlib.redirect_stdout(io.StringIO()) as diagnostics:
        from src.simulator import simulate_protocol
        scenario = json.loads(args.inventory.read_text()) if args.inventory else get_scenario(args.scenario)
        if scenario["id"] != args.scenario:
            raise ValueError("Inventory snapshot does not match scenario")
        result = simulate_protocol(args.protocol.read_text(), scenario)
    result["sdk_diagnostics"] = diagnostics.getvalue()
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n")
    print(payload)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
