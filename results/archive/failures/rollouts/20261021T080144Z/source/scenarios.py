"""Constructed benchmark tasks: volumes are synthetic, not a wet-lab recipe."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scenarios(suite="mixing"):
    if suite not in ("mixing", "ordering", "biochemistry", "biochemistry_ordering", "failures"):
        raise ValueError(f"Unknown task suite: {suite}")
    scenarios = json.loads((ROOT / "data" / f"{suite}_tasks.json").read_text())
    if suite == "ordering":
        from src.fragments import ordering_scenario
        scenarios.append(ordering_scenario())
    if suite in ("biochemistry", "biochemistry_ordering", "failures"):
        from src.fragments import biochemistry_inventory
        for scenario in scenarios:
            scenario["sequence_inventory"] = biochemistry_inventory(scenario)
            for source in scenario["sources"].values():
                name = next(iter(source["components"]))
                if name in scenario["sequence_inventory"]:
                    source["sequence"] = copy.deepcopy(scenario["sequence_inventory"][name])
                    source["concentration_ng_per_ul"] = scenario["biochemistry"]["dna"][name]["concentration_ng_ul"]
    return scenarios


def get_scenario(task_id):
    for scenario in load_scenarios() + load_scenarios("ordering") + load_scenarios("biochemistry") + load_scenarios("biochemistry_ordering") + load_scenarios("failures"):
        if scenario["id"] == task_id:
            return copy.deepcopy(scenario)
    raise ValueError(f"Unknown scenario: {task_id}")
