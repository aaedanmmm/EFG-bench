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
    # Resolve static IDs before loading dynamic partitions from an unrelated suite.
    for suite in ("mixing", "ordering", "biochemistry", "biochemistry_ordering", "failures"):
        raw = json.loads((ROOT / "data" / f"{suite}_tasks.json").read_text())
        if any(item["id"] == task_id for item in raw):
            scenarios = raw if suite == "ordering" else load_scenarios(suite)
            return copy.deepcopy(next(item for item in scenarios if item["id"] == task_id))
    legacy = ROOT / "data/legacy_synthetic_tasks.json"
    if legacy.exists():
        from src.fragments import biochemistry_inventory
        for scenario in json.loads(legacy.read_text()):
            if scenario["id"] == task_id:
                scenario["sequence_inventory"] = biochemistry_inventory(scenario)
                for source in scenario["sources"].values():
                    component = next(iter(source["components"]))
                    if component in scenario["sequence_inventory"]:
                        source["sequence"] = copy.deepcopy(scenario["sequence_inventory"][component])
                        source["concentration_ng_per_ul"] = scenario["biochemistry"]["dna"][component]["concentration_ng_ul"]
                return scenario
    if task_id == "order_sequence_partitions":
        from src.fragments import ordering_scenario
        return copy.deepcopy(ordering_scenario())
    raise ValueError(f"Unknown scenario: {task_id}")
