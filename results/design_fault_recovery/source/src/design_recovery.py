"""Constructed design-plus-recovery scenarios and causal fault interventions.

This extends the sequence design lab, not the OT-2 execution environment.
Private fault metadata is excluded from every agent-visible response.
"""
from copy import deepcopy
import hashlib
import json

from src.design_ordering import catalogue, quote_fragment
from src.scenarios import ROOT

SERVICES = {
    "check_stock": {"price_cents": 4000, "minutes": 10},
    "positive_control": {"price_cents": 4000, "minutes": 20},
    "thermometer_check": {"price_cents": 2000, "minutes": 5},
    "calibrate_temperature": {"price_cents": 6000, "minutes": 15},
}


def load_recovery_scenarios(seed=0):
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise ValueError("Recovery seed must be an integer in 0..2**63-1")
    base = json.loads((ROOT / "data/design_fault_recovery.json").read_text())
    kinds = ["inactive_polymerase", "damaged_stock", "absent_stock", "hot_module", "cold_module"]
    kinds.sort(key=lambda kind: hashlib.sha256(f"design-recovery-v1:{seed}:{kind}".encode()).digest())
    scenarios = []
    for index, kind in enumerate(kinds, 1):
        scenario = deepcopy(base)
        scenario["id"] = f"design_recovery_{index:02d}"
        scenario["recovery_private"] = {"kind": kind, "seed": seed}
        scenarios.append(scenario)
    return scenarios


def initial_state():
    return {"bound": False, "active": True, "stock_id": None, "reagent_id": None,
            "revision": 0, "thermometer_checked": False, "services": []}


def public_recovery():
    return {
        "constructed": True,
        "environment": "sequence design lab; no OT-2 protocol or physical lab execution",
        "possible_faults": ["inactive polymerase", "damaged DNA stock", "absent DNA stock",
                            "temperature offset of +12 or -12 C"],
        "services": deepcopy(SERVICES),
        "rules": [
            "Exactly one hidden persistent fault per task; five task conditions are shuffled by seed.",
            "Reserve repair and diagnostic funds when choosing a polymerase; the cheapest polymerase can meet the yield gate.",
            "The stock fault affects one initial synthesized stock; an enzyme fault affects one initial polymerase lot.",
            "Stock checks report intact length, fragmentation, or no detectable DNA; they do not sequence DNA.",
            "Positive controls use supplied verified inputs on the same block and your chosen purchased polymerase.",
            "Control inputs cannot be ordered, selected, or used to construct your target.",
            "Module setpoint is fixed at 50 C; a check measures actual temperature without repairing it.",
            "Replacement discards the old lot and buys a good lot at its original catalogue/synthesis price.",
            "Ordinary repeat orders do not replace the faulty lot. Calibration requires a prior module check.",
            "Observe low yield on an exact-target design affected by the fault before repairing it.",
            "Then repair, run again, measure and select the latest candidate using current inventory.",
            "Old reactions and already digested stocks retain their original state after repairs.",
            "Diagnostics are deterministic constructed cues; no ambiguous observation channel is used.",
        ],
    }


def after_order(scenario, lab, kind, identifier):
    state = lab["recovery"]
    fault = scenario["recovery_private"]["kind"]
    if not state["bound"]:
        if kind == "order_fragment" and fault in ("damaged_stock", "absent_stock"):
            originals = [key for key, value in lab["fragments"].items() if "left_end" not in value]
            if len(originals) == 2:
                state.update(bound=True, stock_id=identifier)
                lab["fragments"][identifier]["recovery_fault"] = fault
        elif kind == "order_reagent" and fault == "inactive_polymerase":
            from src.design_experiments import polymerases
            if identifier in polymerases():
                state.update(bound=True, reagent_id=identifier)
    # Any new inventory action invalidates final verification of an older run.
    state["revision"] += 1


def run_fault(scenario, lab, stocks, polymerase):
    state = lab["recovery"]
    kind = scenario["recovery_private"]["kind"]
    return (any(stock.get("recovery_fault") for stock in stocks)
            or (state["active"] and (kind in ("hot_module", "cold_module")
                or (kind == "inactive_polymerase" and state["reagent_id"] == polymerase))))


def action(scenario, lab, kind, *, fragment_id=None, item_id=None, service=None, polymerase=None):
    # Imported lazily to keep the shared lab's dependency direction acyclic.
    from src.design_lab import _charge, _lookup, _require_reagent
    state = lab["recovery"]
    fault = scenario["recovery_private"]["kind"]
    if kind == "replace_design_stock":
        stock = _lookup(lab["fragments"], fragment_id, "DNA fragment")
        if "left_end" in stock or "right_end" in stock:
            raise ValueError("Replace a synthesized stock, then digest again if needed.")
        price = quote_fragment(stock["sequence"], scenario["synthesis"])["price_cents"]
        _charge(scenario, lab, price)
        stock.pop("recovery_fault", None)
        if state["stock_id"] == fragment_id:
            state["active"] = False
        state["revision"] += 1
        return {"fragment_id": fragment_id, "replaced": True, "price_cents": price}
    if kind == "replace_design_reagent":
        _require_reagent(lab, item_id)
        price = catalogue()[item_id]["price_cents"]
        _charge(scenario, lab, price)
        if state["reagent_id"] == item_id:
            state["active"] = False
        state["revision"] += 1
        return {"item_id": item_id, "replaced": True, "price_cents": price}
    if kind != "design_recovery_service" or service not in SERVICES:
        raise ValueError("Unknown recovery action or service")
    result = {"service": service, "constructed": True}
    if service == "check_stock":
        if polymerase is not None:
            raise ValueError("Stock checks require only fragment_id")
        stock = _lookup(lab["fragments"], fragment_id, "DNA fragment")
        condition = stock.get("recovery_fault")
        result.update(fragment_id=fragment_id, bands_bp=[], smear_range_bp=None)
        if condition == "damaged_stock":
            result["smear_range_bp"] = [50, max(51, len(stock["sequence"]) // 2)]
            result["finding"] = "Expected intact band absent; low-size fragmentation smear."
        elif condition == "absent_stock":
            result["finding"] = "No detectable DNA."
        else:
            result.update(bands_bp=[len(stock["sequence"])], finding="Intact band at the nominal stock length.")
    else:
        if fragment_id is not None:
            raise ValueError("This service does not accept fragment_id")
        if service == "positive_control":
            from src.design_experiments import polymerases
            if polymerase not in polymerases():
                raise ValueError("Choose a catalogue polymerase for the control")
            _require_reagent(lab, polymerase)
            failed = run_fault(scenario, lab, [], polymerase)
            result.update(polymerase=polymerase, finding="failed" if failed else "passed",
                          explanation="Verified control inputs; tests the chosen enzyme and shared temperature block.")
        else:
            if polymerase is not None:
                raise ValueError("Module services do not accept polymerase")
            if service == "thermometer_check":
                offset = (12 if fault == "hot_module" else -12 if fault == "cold_module" else 0) if state["active"] else 0
                result.update(setpoint_c=50, measured_temperature_c=50 + offset)
                state["thermometer_checked"] = True
            else:
                if not state["thermometer_checked"]:
                    raise ValueError("Request a thermometer_check before calibration")
                if fault in ("hot_module", "cold_module"):
                    state["active"] = False
                state["revision"] += 1
                result["calibration_performed"] = True
    config = SERVICES[service]
    _charge(scenario, lab, config["price_cents"])
    lab["minutes"] += config["minutes"]
    state["services"].append(deepcopy(result))
    return {**result, "price_cents": config["price_cents"]}


def grade_recovery(scenario, lab, selected):
    # A witnessed failure must be measured before the repair, not retrospectively.
    failed = lab["recovery"].get("witnessed_failures", [])
    run = lab["experiments"].get(selected, {})
    current = (selected == next(reversed(lab["experiments"]), None)
               and run.get("recovery_revision") == lab["recovery"]["revision"])
    resolved = not lab["recovery"]["active"]
    return {"passed": bool(failed and current and resolved), "observed_failed_experiments": failed,
            "fault_resolved": resolved, "current_verification": current,
            "private_fault": deepcopy(scenario["recovery_private"])}
