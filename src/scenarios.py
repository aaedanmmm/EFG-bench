"""Constructed benchmark tasks: volumes are synthetic, not a wet-lab recipe."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scenarios(suite="mixing"):
    if suite not in ("mixing", "ordering", "biochemistry"):
        raise ValueError(f"Unknown task suite: {suite}")
    return json.loads((ROOT / "data" / f"{suite}_tasks.json").read_text())


def get_scenario(task_id):
    for scenario in load_scenarios() + load_scenarios("ordering") + load_scenarios("biochemistry"):
        if scenario["id"] == task_id:
            return copy.deepcopy(scenario)
    raise ValueError(f"Unknown scenario: {task_id}")
