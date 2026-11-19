"""Persistent synthetic lab faults and paid, simulated human services.

Band patterns and prices are constructed benchmark rules, not measured assays
or uniquely diagnostic biology. No real person or supplier is contacted.
"""
import copy
import hashlib
import json
import math
from src.ordering import OrderError, new_account, place_order
from src import observations

# Constructed labour pricing: technician hours x a fully loaded hourly rate
# (wage plus benefits and institutional overhead, roughly 1.4-1.6x a ~$25-30/h
# US lab-technician wage). Hours count the technician's occupied time, including
# setup and cleanup, but not unattended instrument time. Consumables excluded.
TECHNICIAN_RATE_CENTS_PER_HOUR = 4000
SERVICES = {
    "run_gel": {"technician_hours": 1.0, "description": "Human casts a gel, loads and runs one simulated DNA lane with a ladder, images it and cleans up (~60 min hands-on, ~1.5 h elapsed)."},
    "thermometer_check": {"technician_hours": 0.5, "description": "Human places a calibrated probe in the block, waits for equilibration and records the temperature (~30 min); does not repair it."},
    "calibrate_temperature": {"technician_hours": 1.5, "description": "Human measures several setpoints, applies the offset correction, re-verifies and documents it (~90 min) after a thermometer check; permanently removes its offset."},
}
for _service in SERVICES.values():
    _service.update(price_cents=round(_service["technician_hours"] * TECHNICIAN_RATE_CENTS_PER_HOUR), technician_rate_cents_per_hour=TECHNICIAN_RATE_CENTS_PER_HOUR)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def active_faults(scenario):
    return [f for f in scenario.get("failure_modes", []) if f.get("active", True)]


def temperature_offset(scenario, slot):
    return sum(f["offset_c"] for f in active_faults(scenario) if f["kind"] == "temperature_offset" and f["module_slot"] == slot)


def repair_from_order(scenario, item, destination, replace, lot_id):
    """Good replacement stock clears only faults attached to that source."""
    if not replace or item["category"] != "reagent":
        return
    for fault in active_faults(scenario):
        if fault["kind"] != "temperature_offset" and fault["source_well"] == destination and fault["component"] == item["component"]:
            fault.update(active=False, resolved_by={"kind": "replacement_order", "lot_id": lot_id})


def human_service(scenario, account, service, sample="", sample_type="reaction", module_slot="4", setpoint_c=50, request_id=""):
    """Atomic, idempotent charge/state transition; no assay is generated here."""
    if not scenario.get("failure_modes") or account is None:
        raise OrderError("Failure-mode services are not enabled for this task")
    if service not in SERVICES:
        raise OrderError("Unknown human service")
    if not isinstance(request_id, str) or len(request_id) > 80:
        raise OrderError("request_id must be text of at most 80 characters")
    request = {"service": service, "sample": sample, "sample_type": sample_type, "module_slot": module_slot, "setpoint_c": setpoint_c, "request_id": request_id}
    for previous in account.get("human_services", []):
        if request_id and previous["request"]["request_id"] == request_id:
            if previous["request"] != request:
                raise OrderError("request_id already belongs to a different human service")
            return copy.deepcopy(scenario), copy.deepcopy(account), copy.deepcopy(previous)
    if service == "run_gel":
        valid = scenario["sources"] if sample_type == "source" else scenario["biochemistry"]["reaction_wells"] if sample_type == "reaction" else []
        if sample not in valid:
            raise OrderError("Gel sample must be a configured source or reaction well")
    else:
        if module_slot not in scenario.get("modules", {}):
            raise OrderError("Unknown temperature-module slot")
        if type(setpoint_c) not in (int, float) or not math.isfinite(setpoint_c) or not 4 <= setpoint_c <= 95:
            raise OrderError("Thermometer setpoint must be within 4..95 C")
        if service == "calibrate_temperature" and not any(r["request"]["service"] == "thermometer_check" and r["request"]["module_slot"] == module_slot for r in account.get("human_services", [])):
            raise OrderError("Request a thermometer_check on this module before calibration")
    price = SERVICES[service]["price_cents"]
    if account["spent_cents"] + price > account["budget_cents"]:
        raise OrderError("Insufficient budget for human service")
    updated, charged = copy.deepcopy(scenario), copy.deepcopy(account)
    service_id = f"human-{len(charged.get('human_services', [])) + 1:04d}"
    result = {"status": "completed", "simulated_human": True}
    if service == "thermometer_check":
        offset = temperature_offset(updated, module_slot)
        result.update(module_slot=module_slot, requested_setpoint_c=setpoint_c, calibration_performed=False)
        if observations.enabled(updated):
            result.update(observations.measurement(updated, sample_id=f"module:{module_slot}",
                          measurement_id=service_id, deviates=offset != 0))
        else:
            result.update(measured_temperature_c=setpoint_c + offset, offset_c=offset)
    if service == "calibrate_temperature":
        for fault in active_faults(updated):
            if fault["kind"] == "temperature_offset" and fault["module_slot"] == module_slot:
                fault.update(active=False, resolved_by={"kind": "human_calibration", "service_id": service_id})
        result.update(module_slot=module_slot, calibration_performed=True)
        if not observations.enabled(updated):
            result["remaining_offset_c"] = temperature_offset(updated, module_slot)
    charged["spent_cents"] += price
    receipt = {"service_id": service_id, "request": request, "currency": "USD", "total_cents": price, "remaining_cents": charged["budget_cents"] - charged["spent_cents"], "result": result}
    charged.setdefault("human_services", []).append(receipt)
    return updated, charged, copy.deepcopy(receipt)


def replay_lab_actions(original, actions):
    """Rebuild stock, fault resolutions and costs; never trust mutable receipts."""
    scenario, account = copy.deepcopy(original), new_account(original)
    for action in actions:
        if action["kind"] == "order":
            scenario, account, _ = place_order(scenario, account, **action["request"])
        elif action["kind"] == "human_service":
            scenario, account, _ = human_service(scenario, account, **action["request"])
        else:
            raise OrderError("Unknown laboratory action")
    return scenario, account


def assess_failures(scenario, report):
    """Reactions fail under a persistent fault despite correct nominal volumes."""
    if not scenario.get("failure_modes"):
        return
    faults = active_faults(scenario)
    report["failure_mode_assessment"] = {
        "constructed": True, "active_faults": copy.deepcopy(faults),
        "resolved_faults": [copy.deepcopy(f) for f in scenario["failure_modes"] if not f.get("active", True)],
        "passed": not faults,
    }
    if faults:
        report["passed"] = False
        report["errors"].append("Reaction outcome failed; obtain diagnostic observations with the laboratory service tools")
        bio = report.get("biochemistry", {})
        if bio.get("applicable"):
            bio["passed"], bio["status"] = False, "in_silico_conditions_failed"
            bio["checks"].append({"id": "reaction.assembly_outcome", "passed": False, "observed": "Expected complete product not obtained", "expected": "Complete expected assembly", "basis": "constructed persistent-fault benchmark"})


def without_incubation_details(report):
    """Project feedback without revealing hidden-temperature-derived evidence.

    A pass/fail gate or its error reveals the same information as qualifying
    seconds. Keep all three private, including for non-recovery dry runs. Work
    on a copy so experiments, paid assays and final grading retain full evidence.
    """
    result = copy.deepcopy(report)
    bio = result.get("biochemistry", {})
    checks = bio.get("checks", [])
    incubation_ids = {
        check["id"] for check in checks
        if check.get("id", "").endswith(".incubation")
    }
    if "checks" in bio:
        bio["checks"] = [check for check in checks if check.get("id") not in incubation_ids]
    for reaction in bio.get("reactions", []):
        reaction.pop("qualified_incubation_seconds", None)
    if "errors" in result:
        private_errors = {f"Biochemistry: {check_id}" for check_id in incubation_ids}
        result["errors"] = [error for error in result["errors"] if error not in private_errors]
    return result


def public_feedback(report):
    """Do not disclose hidden faults or actual-temperature-derived evidence."""
    result = without_incubation_details(report)
    result.pop("failure_mode_assessment", None)
    for key in ("events", "opentrons_commands", "sdk_diagnostics"):
        result.pop(key, None)
    assembly = result.get("biochemistry", {}).get("assembly", {})
    assembly.pop("predicted_sequence", None)
    assembly.pop("expected_sequence", None)
    for check in result.get("biochemistry", {}).get("checks", []):
        if isinstance(check.get("observed"), dict):
            check["observed"].pop("all_incubation_events", None)
    return result


def sequence_lengths(scenario):
    return {name: scenario["sequence_inventory"][name]["length_bp"] for name in scenario["biochemistry"]["dna"]}


def diagnostic_reference(scenario):
    """Public size/location reference; derived only from declared inputs, never faults."""
    from src.biochemistry import load_assembly_inputs
    spec = scenario["biochemistry"]
    assembly = load_assembly_inputs(scenario, spec)
    lengths = sequence_lengths(scenario)
    result = {
        "constructed": True,
        "size_unit": "bp",
        "band_sizes": "Approximate benchmark size estimates, not measured gel resolution",
        "expected_product_size_bp": len(assembly.expected_product),
        "dna_sources": [
            {"source_well": well, "component": component, "expected_intact_band_bp": lengths[component],
             **({"raw_core_length_bp": scenario["sequence_inventory"][component]["core_length_bp"], "added_overlap_bp": scenario["sequence_inventory"][component]["three_prime_overlap_bp"]} if "raw_input" in scenario["sequence_inventory"][component] else {})}
            for well, source in scenario["sources"].items()
            for component in source["components"] if component in lengths
        ],
        "acceptable_incubation_temperature_c": list(spec["criteria"]["temperature_c"]),
        "diagnostic_limits": [
            "Compare source-stock bands with each input's expected intact size. An empty lane indicates no detectable DNA; smaller bands or a smear indicate poor stock quality in this benchmark.",
            "A failed reaction lane alone need not identify the defective input. Test individual DNA sources to localize damage or absence; identical-size inputs cannot be distinguished by size in a pooled lane.",
            "Unassembled input-size reaction bands can reflect enzyme inactivity or incorrect block temperature. A gel alone cannot determine whether the block is too hot or too cold. Request a thermometer check and compare measured temperature with its setpoint.",
            "An expected product-size band is the benchmark's success observation, not proof of real sequence identity or biochemical success.",
        ],
    }
    if observations.enabled(scenario):
        result["diagnostic_limits"] = [
            "All observations use the disclosed abstract probability model, not a physical assay simulation.",
            "Each finding can occur with or without a deviation. A reaction observation cannot identify a cause.",
            "Source observations concern the sampled stock, module observations concern its offset, and reaction observations concern the immutable experiment outcome.",
            "Repeated measurements share sample quality. Neither a reassuring finding nor an inconclusive finding establishes success.",
        ]
    return result


def gel_assay(scenario, sample, sample_type, *, experiment=None, measurement_id=""):
    """Symptoms derive from an immutable experiment snapshot, never current repairs."""
    if observations.enabled(scenario):
        return ambiguous_assay(scenario, sample, sample_type, experiment=experiment, measurement_id=measurement_id)
    lengths, faults = sequence_lengths(scenario), active_faults(scenario)
    bands, smear = [], None
    result = {"constructed": True, "assay": "synthetic_gel_v1", "sample": sample, "sample_type": sample_type,
              "interpretation": "Stylized benchmark bands; not measured or uniquely diagnostic. Reaction sizes use a linearized-product diagnostic convention."}
    if sample_type == "source":
        if sample not in scenario["sources"]:
            raise OrderError("Unknown DNA source well")
        source = scenario["sources"][sample]
        component = next(iter(source["components"]))
        if component not in lengths:
            raise OrderError("Source gel requires a DNA stock")
        expected = lengths[component]
        relevant = [f for f in faults if f.get("source_well") == sample]
        if any(f["kind"] == "absent_dna" for f in relevant) or sum(source["components"].values()) <= 0:
            observation = "No detectable DNA band in this stock lane"
        elif any(f["kind"] == "damaged_dna" for f in relevant):
            bands = [max(1, round(expected * 0.28)), max(2, round(expected * 0.61))]
            smear = [max(1, round(expected * 0.05)), max(2, round(expected * 0.8))]
            observation = "Expected intact fragment band absent; low-size smear and additional products"
        else:
            bands, observation = [expected], "Single intact stock band at the expected size"
        result.update(component=component, expected_size_bp=expected, inventory_sha256=fingerprint(scenario))
    elif sample_type == "reaction":
        if experiment is None:
            raise OrderError("Simulate a protocol before requesting a reaction gel")
        scenario, report = experiment["scenario"], experiment["report"]
        if sample not in scenario["biochemistry"]["reaction_wells"]:
            raise OrderError("Unknown reaction well")
        lengths, faults = sequence_lengths(scenario), active_faults(scenario)
        expected = len(report.get("biochemistry", {}).get("assembly", {}).get("expected_sequence", ""))
        if not expected or not report.get("liquid_handling_passed"):
            raise OrderError("No interpretable reaction; fix execution/configuration before assaying")
        if any(f["kind"] == "inactive_ligase" for f in faults):
            bands, observation = sorted(set(lengths.values())), "Multiple lower-size bands; expected complete product band absent"
        elif any(f["kind"] == "damaged_dna" for f in faults):
            bands = [round(expected * 0.25), round(expected * 0.55)]
            smear, observation = [80, round(expected * 0.7)], "Low-size smear or multiple off-target products; expected complete product absent"
        elif any(f["kind"] == "absent_dna" for f in faults):
            bands, observation = [round(expected * 0.60), round(expected * 0.82)], "Two large incomplete products; expected full-size product absent; compare individual stock lanes"
        elif any(f["kind"] == "temperature_offset" for f in faults):
            bands, observation = sorted(set(lengths.values())), "Weak incomplete products; expected full-size product absent despite the programmed incubation"
        elif report["passed"]:
            bands, observation = [expected], "Single expected full-size product band"
        else:
            bands, observation = sorted(set(lengths.values())), "Expected product absent; nominal assembly conditions failed"
        result.update(expected_size_bp=expected, experiment_id=experiment["id"], protocol_sha256=experiment["protocol_sha256"], inventory_sha256=experiment["inventory_sha256"])
    else:
        raise OrderError("sample_type must be source or reaction")
    result.update(bands_bp=bands, smear_range_bp=smear, observation=observation)
    return result


def ambiguous_assay(scenario, sample, sample_type, *, experiment, measurement_id):
    """Project a private condition into a generic categorical observation."""
    result = {"assay": "abstract_reference_check_v1", "sample": sample, "sample_type": sample_type}
    if sample_type == "source":
        if sample not in scenario["sources"]:
            raise OrderError("Unknown DNA source well")
        source = scenario["sources"][sample]
        component = next(iter(source["components"]))
        if component not in sequence_lengths(scenario):
            raise OrderError("Source gel requires a DNA stock")
        deviates = (sum(source["components"].values()) <= 0 or
                    any(f.get("source_well") == sample for f in active_faults(scenario)))
        sample_id = f"source:{sample}:{source.get('lot_id', 'preloaded')}"
        result.update(component=component, inventory_sha256=fingerprint(scenario))
    elif sample_type == "reaction":
        if experiment is None:
            raise OrderError("Simulate a protocol before requesting a reaction gel")
        scenario = experiment["scenario"]
        if sample not in scenario["biochemistry"]["reaction_wells"]:
            raise OrderError("Unknown reaction well")
        if not experiment["report"].get("liquid_handling_passed"):
            raise OrderError("No interpretable reaction; fix execution/configuration before assaying")
        deviates = not experiment["report"]["passed"]
        sample_id = f"reaction:{experiment['id']}:{sample}"
        result.update(experiment_id=experiment["id"], protocol_sha256=experiment["protocol_sha256"],
                      inventory_sha256=experiment["inventory_sha256"])
    else:
        raise OrderError("sample_type must be source or reaction")
    result.update(observations.measurement(scenario, sample_id=sample_id,
                  measurement_id=measurement_id, deviates=deviates))
    return result


def recovery_evidence(original, actions, experiments, assays, code, final_report, final_inventory):
    """Verify paid observations against trusted action replay and final execution.

    The workspace is tool-owned (protocol code cannot access it). Replay still
    rejects fabricated receipts, stale code/stock and assays without a paid action.
    """
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    final_hash = fingerprint(final_inventory)
    observed_failure, verified_success, current_measurement = False, False, False
    accepted = []
    for assay in assays:
        count = assay.get("action_count", 0)
        if type(count) is not int or not 1 <= count <= len(actions):
            continue
        action = actions[count - 1]
        if action.get("kind") != "human_service" or action.get("request", {}).get("service") != "run_gel":
            continue
        _, account = replay_lab_actions(original, actions[:count])
        receipt = account["human_services"][-1]
        if receipt["service_id"] != assay.get("service_id") or receipt["request"]["sample"] != assay.get("sample") or receipt["request"]["sample_type"] != "reaction":
            continue
        experiment = next((e for e in experiments if e["id"] == assay.get("experiment_id")), None)
        if experiment is None or not 0 <= experiment.get("action_count", -1) < count:
            continue
        inventory, _ = replay_lab_actions(original, actions[:experiment["action_count"]])
        if fingerprint(inventory) != experiment.get("inventory_sha256") or fingerprint(experiment["scenario"]) != fingerprint(inventory):
            continue
        expected = gel_assay(inventory, assay["sample"], "reaction", experiment=experiment,
                             measurement_id=receipt["service_id"])
        if any(assay.get(key) != value for key, value in expected.items()):
            continue
        before_assay, _ = replay_lab_actions(original, actions[:count])
        adverse_observation = (assay.get("finding") == "deviation_detected") if observations.enabled(original) else True
        if adverse_observation and active_faults(inventory) and active_faults(before_assay) and experiment["report"].get("liquid_handling_passed") and not experiment["report"]["passed"]:
            observed_failure = True
        current = experiment["protocol_sha256"] == code_hash and experiment["inventory_sha256"] == final_hash
        if observations.enabled(original):
            current = current and bool(experiments) and experiment["id"] == experiments[-1]["id"]
        current_measurement |= current
        acceptable_observation = (True if observations.enabled(original) else
                                  assay["bands_bp"] == [assay["expected_size_bp"]] and assay["smear_range_bp"] is None)
        if current and final_report["passed"] and experiment["report"]["passed"] and acceptable_observation:
            verified_success = True
        accepted.append(copy.deepcopy(assay))
    passed = (observed_failure or not original["recovery"].get("require_failed_reaction_gel")) and (verified_success or not original["recovery"].get("require_final_reaction_gel"))
    result = {"passed": bool(passed), "failed_reaction_observed": observed_failure, "current_success_verified": verified_success, "assays": accepted}
    if observations.enabled(original):
        result.update(current_measurement_recorded=current_measurement,
                      verification_basis="Private replay outcome plus a paid current measurement; a reassuring reading is neither necessary nor sufficient")
    return result
