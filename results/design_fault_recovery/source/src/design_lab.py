"""Replayable purchases, experiments and measurements for the gene design task."""
from copy import deepcopy

from src.design_assembly import assemble, digest
from src.design_experiments import (
    experiment_quality,
    measure_yield,
    public_experiment,
    run_experiment,
)
from src.design_ordering import catalogue, quote_fragment

DIGEST_MINUTES = 15
ASSAY_MINUTES = 5


def new_lab():
    return {
        "minutes": 0,
        "spent_cents": 0,
        "fragments": {},
        "reagents": {},
        "experiments": {},
        "measurements": {},
        "selected": None,
        "actions": [],
    }


def _charge(scenario, lab, cents):
    remaining = scenario["budget_cents"] - lab["spent_cents"]
    if cents > remaining:
        raise ValueError(f"Insufficient budget: {cents} cents needed, {remaining} cents left.")
    lab["spent_cents"] += cents


def _lookup(collection, identifier, kind):
    if identifier not in collection:
        raise ValueError(f"Unknown {kind}: {identifier}")
    return collection[identifier]


def _add_fragment(lab, sequence, **ends):
    identifier = f"dna-{len(lab['fragments']) + 1}"
    lab["fragments"][identifier] = {"sequence": sequence, **ends}
    return identifier


def _order_fragment(scenario, lab, sequence):
    quote = quote_fragment(sequence, scenario["synthesis"])
    _charge(scenario, lab, quote["price_cents"])
    identifier = _add_fragment(lab, quote["sequence"])
    return {"fragment_id": identifier, "length_bp": quote["length_bp"], "price_cents": quote["price_cents"]}


def _order_reagent(scenario, lab, item_id):
    item = _lookup(catalogue(), item_id, "catalogue item")
    _charge(scenario, lab, item["price_cents"])
    lab["reagents"][item_id] = lab["reagents"].get(item_id, 0) + 1
    return {"item_id": item_id, "packs": lab["reagents"][item_id], "price_cents": item["price_cents"]}


def _require_reagent(lab, item_id):
    if item_id not in lab["reagents"]:
        raise ValueError(f"Order {item_id} before use.")


def _digest_fragment(scenario, lab, fragment_id, enzyme):
    fragment = _lookup(lab["fragments"], fragment_id, "DNA fragment")
    _require_reagent(lab, enzyme)
    if "left_end" in fragment or "right_end" in fragment:
        raise ValueError("Use a synthesized precursor for a restriction digest.")
    products = digest(fragment["sequence"], enzyme)
    if "recovery" in lab:
        lab["recovery"]["revision"] += 1
        if fragment.get("recovery_fault"):
            for product in products:
                product["recovery_fault"] = fragment["recovery_fault"]
    lab["minutes"] += DIGEST_MINUTES
    return {
        "products": [
            {"fragment_id": _add_fragment(lab, **product),
             **{key: value for key, value in product.items() if key != "recovery_fault"}}
            for product in products
        ],
    }


def _run_assembly(scenario, lab, fragment_ids, polymerase):
    if not 2 <= len(fragment_ids) <= 20 or len(set(fragment_ids)) != len(fragment_ids):
        raise ValueError("Supply 2–20 distinct stock IDs in assembly order.")
    stocks = [_lookup(lab["fragments"], item, "DNA fragment") for item in fragment_ids]
    _require_reagent(lab, polymerase)
    experiment = run_experiment(
        scenario["experiments"], polymerase, len(stocks), lab["minutes"]
    )
    try:
        inputs = [stock if "left_end" in stock or "right_end" in stock else stock["sequence"] for stock in stocks]
        product = assemble(inputs, scenario["assembly"])
    except ValueError:
        product = None
        experiment["initial_yield_ng"] = 0.0
        experiment["initial_correct_yield_ng"] = 0.0
        experiment["correct_fraction"] = 0.0
    identifier = f"run-{len(lab['experiments']) + 1}"
    recovery_snapshot = {}
    if "recovery" in lab:
        from src.design_recovery import run_fault
        affected = run_fault(scenario, lab, stocks, polymerase)
        recovery_snapshot = {
            "fault_caused_failure": affected and product == scenario["target_sequence"],
            "recovery_revision": lab["recovery"]["revision"],
        }
        if affected:
            experiment.update(initial_yield_ng=0.0, initial_correct_yield_ng=0.0)
    lab["experiments"][identifier] = {
        "experiment": experiment, "product": product, "fragment_ids": fragment_ids,
        **recovery_snapshot,
    }
    lab["minutes"] = experiment["finished_at_minutes"]
    return {"experiment_id": identifier, **public_experiment(experiment)}


def _assay(scenario, lab, experiment_id):
    run = _lookup(lab["experiments"], experiment_id, "experiment")
    _charge(scenario, lab, scenario["assay_price_cents"])
    lab["minutes"] += ASSAY_MINUTES
    reading = measure_yield(run["experiment"], lab["minutes"], scenario["experiments"])
    lab["measurements"].setdefault(experiment_id, []).append(reading)
    if ("recovery" in lab and lab["recovery"]["active"]
            and run.get("fault_caused_failure")):
        lab["recovery"].setdefault("witnessed_failures", []).append(experiment_id)
    return {"experiment_id": experiment_id, **reading}


def _wait(scenario, lab, minutes):
    if type(minutes) is not int or not 1 <= minutes <= scenario["deadline_minutes"]:
        raise ValueError("Wait must be a positive whole number of minutes within the task deadline.")
    lab["minutes"] += minutes
    return {}


def _select(scenario, lab, experiment_id):
    _lookup(lab["experiments"], experiment_id, "experiment")
    lab["selected"] = experiment_id
    return {"experiment_id": experiment_id}


_ACTIONS = {
    "order_fragment": _order_fragment,
    "order_reagent": _order_reagent,
    "digest_fragment": _digest_fragment,
    "run_assembly": _run_assembly,
    "measure_yield": _assay,
    "wait": _wait,
    "select_product": _select,
}


def apply_action(scenario, lab, kind, **arguments):
    """Commit a complete action or leave its input state untouched."""
    updated = deepcopy(lab)
    if "recovery_private" in scenario and "recovery" not in updated:
        from src.design_recovery import initial_state
        updated["recovery"] = initial_state()
    if kind in ("replace_design_stock", "replace_design_reagent", "design_recovery_service"):
        if "recovery" not in updated:
            raise ValueError("Recovery actions require the design_fault_recovery suite")
        from src.design_recovery import action
        result = action(scenario, updated, kind, **arguments)
    else:
        if kind not in _ACTIONS:
            raise ValueError(f"Unknown design action: {kind}")
        result = _ACTIONS[kind](scenario, updated, **arguments)
    if "recovery" in updated and kind in ("order_fragment", "order_reagent"):
        from src.design_recovery import after_order
        after_order(scenario, updated, kind, result.get("fragment_id", result.get("item_id")))
    if updated["minutes"] > scenario["deadline_minutes"]:
        raise ValueError(f"Action would finish after the {scenario['deadline_minutes']}-minute deadline.")
    updated["actions"].append({"kind": kind, "arguments": deepcopy(arguments)})
    return updated, {
        **result,
        "minutes": updated["minutes"],
        "remaining_cents": scenario["budget_cents"] - updated["spent_cents"],
    }


def public_lab(scenario, lab):
    return {
        "minutes": lab["minutes"],
        "remaining_cents": scenario["budget_cents"] - lab["spent_cents"],
        "stock": {key: len(value["sequence"]) for key, value in lab["fragments"].items()},
        "reagents": deepcopy(lab["reagents"]),
        "experiments": {
            key: public_experiment(run["experiment"]) for key, run in lab["experiments"].items()
        },
        "measurements": deepcopy(lab["measurements"]),
        "selected": lab["selected"],
        **({"recovery_services": deepcopy(lab["recovery"]["services"])} if "recovery" in lab else {}),
    }


def grade_lab(scenario, actions):
    """Rebuild stocks, products and aging from action arguments and private config."""
    lab = new_lab()
    for action in actions:
        lab, _ = apply_action(scenario, lab, action["kind"], **action["arguments"])

    selected = lab["selected"]
    run = lab["experiments"].get(selected)
    matches = run is not None and run["product"] == scenario["target_sequence"]
    readings = lab["measurements"].get(selected, [])
    quality = (
        experiment_quality(run["experiment"], lab["minutes"], scenario["experiments"])
        if run is not None else None
    )
    if quality is not None and not matches:
        quality.update(correct_yield_ng=0.0, correct_fraction=0.0)
    passed = bool(matches and readings and quality["correct_yield_ng"] >= scenario["minimum_correct_yield_ng"])
    recovery = None
    if "recovery_private" in scenario:
        from src.design_recovery import grade_recovery, initial_state
        lab.setdefault("recovery", initial_state())
        recovery = grade_recovery(scenario, lab, selected)
        passed = passed and recovery["passed"]
    return {
        "passed": passed,
        "exact_product": matches,
        "selected_experiment": selected,
        "fragment_ids": run["fragment_ids"] if run is not None else [],
        "polymerase": run["experiment"]["polymerase"] if run is not None else None,
        "selected_measurements": readings,
        "quality_at_submission": quality,
        "elapsed_minutes": lab["minutes"],
        "spent_cents": lab["spent_cents"],
        "budget_cents": scenario["budget_cents"],
        "cost_efficiency": 1 - lab["spent_cents"] / scenario["budget_cents"] if passed else 0.0,
        **({"recovery": recovery} if recovery is not None else {}),
    }
