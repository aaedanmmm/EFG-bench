"""Sample-scoped agent workspace. Tools never execute arbitrary agent Python."""
import copy
import json
import hashlib
from inspect_ai.solver import solver
from inspect_ai.tool import tool, ToolError
from inspect_ai.util import store
from src.runner import validate_code
from src.costs import get_catalogue
from src.ordering import OrderError, account_summary, new_account, place_order, public_scenario

API_GUIDE = """
Write normal OT-2 Python with metadata={'apiLevel': '2.19'} and one
run(protocol) function. Optional: from opentrons import protocol_api and a
protocol_api.ProtocolContext annotation. No other imports or helper functions.
Use local variables, literal lists/tuples/dicts, indexing, arithmetic, for loops,
if comparisons, range, zip, enumerate, len. Up to 384 loop items and 20,000
interpreter steps. No comprehensions, while, try, classes, mutation of objects,
f-strings, arbitrary attribute access, filesystem, network or dynamic Python.

Available methods (all arguments must be passed as in these signatures):
protocol.load_labware(load_name, location, label=None)
protocol.load_instrument(instrument_name, mount, tip_racks=[tips])
protocol.comment(msg)
protocol.load_module(module_name, location)
module.load_labware(load_name), module.set_temperature(celsius), module.deactivate()
protocol.delay(seconds=0, minutes=0)  # >0 and <=7200 seconds per call
Modules must be explicitly configured in the task. Load their labware through
the module. set_temperature waits for the virtual setpoint; only delay records
incubation exposure. A comment about heating does not heat a sample.
labware['A1'], labware.wells(), wells_by_name(), rows(), columns()
pipette.pick_up_tip(location=None), pipette.drop_tip()
pipette.aspirate(volume, location, rate=1.0)
pipette.dispense(volume, location, rate=1.0)
pipette.blow_out(location)
pipette.mix(repetitions, volume, location, rate=1.0)
pipette.transfer(volume, source, dest, new_tip='always', mix_after=None)
Transfer takes one source, one destination, one scalar volume <=200 uL,
new_tip 'always' or 'never'. It splits volumes over pipette capacity into equal
chunks. Use loops for multiple wells. No implicit locations or well offsets.

Load only the specified labware, pipette and tip racks. Sources start with the
specified stock volumes. All other wells start empty. Volumes are uL. Aspirates
must leave stock dead volumes intact. Pipette aliquots must be 1..20 uL. Every
dispense conservatively counts as tip contact with the destination contents;
a tip that has touched a mixture cannot return to a different stock. Drop tips
rather than returning them. A fresh tip avoids carryover. Final tips must be
dropped. Mix each final target with at least the specified cycles and volume
AFTER its last liquid change. Mixing may occur on the final transfer via
mix_after=(cycles, volume). Transfer and mix require an initially empty tip.
For dilution tasks, also mix intermediate mixtures before sampling them.

Simulation starts from fresh inventory on every call and the final scorer
independently reruns the saved code. Tool results and prose cannot set a score.
Correctness requires all target component volumes within tolerance, explicit
mixing, no unintended liquid outside sources/targets/designated waste wells,
no liquid-handling error, and meeting the tip budget. Efficiency is reported
as tips used and 1 - tips_used/(tip_budget+1), gated on correctness.

Ordering tasks also expose list_catalogue, read_sequence, and order_supplies.
DNA catalogue entries point to validated local FASTA files and include their lengths
and hashes. Source concentrations and aliquot volumes are benchmark assumptions.
The supplied data/sequences partitions have no designed overlaps. Biochemical
tasks use their separate synthetic, overlap-designed sequence inputs. All purchases are
simulated, delivered immediately, and charged in integer USD cents. Reagents go
to their assigned source wells; consumables go to matching configured deck slots.
Inventory and charges persist between dry runs, but simulated liquid/tip use does
not consume planning stock. Budget and order receipts are visible in get_environment.
Failed lots are discovered on aspiration; order a replacement with replace=true.
Replacement discards previous stock without a refund. Lot failures are synthetic
and deterministic. The scorer rebuilds purchased inventory from accepted orders.
Cost efficiency is reported as 1 - spent_cents/budget_cents, gated on correctness.

These tasks and inventory are constructed. The SDK checks virtual robot
commands; the additional liquid ledger assumes ideal homogeneous liquids.
Biochemistry tasks additionally require the declared Gibson acceptance gates:
DNA mass/molar ratios, enzyme mix concentration and supplied activity flag,
exact unique terminal homology, full circular product sequence identity, and
incubation after the final additions and mixing. Inspect biochemistry in the
scenario for all thresholds and references. simulate_protocol returns every gate.
Passing is an in-silico assessment, not an experimental observation. The model
does not estimate yield, kinetics, liquid height, pipetting error, residual films,
or biological function. No physical robot is used.

Failure-recovery tasks expose list_human_services and request_human_service.
Fault identities are hidden. Silent stock problems produce failed reaction
outcomes rather than aspiration exceptions. Obtain a reaction gel after running
simulate_protocol, then use source DNA gel lanes or a human thermometer check
to investigate. Failed enzyme activity can require replacement of the enzyme-
containing master mix. Damaged or absent DNA requires replacement of the affected
stock (replace=true); topping up does not remove a bad lot. Temperature checks
measure a block but do not repair it: request calibration after checking it.
The paid human actions here are simulated, immediate, and charged to the same
budget as orders. Prices are benchmark assumptions. No external person is contacted.
Gels are stylized, constructed diagnostic observations, not unique biological
proof. DNA damage is represented by loss of the intact input band, a smear or
extra bands. Reaction lanes use a linearized-product diagnostic convention.

Repairs persist and are never randomly reintroduced by another dry run. Existing
reaction samples are immutable: ordering or calibration cannot fix an already
failed sample. Simulate again after repair, then request a gel of the NEW reaction.
The recovery suite requires a failed reaction gel before fixing the problem,
and a passing final reaction gel for the exact current protocol and inventory.
Changing code or stock after a gel requires another simulation and final gel.
Dry-run liquid and tip consumption still resets; orders and service charges persist.
""".strip()


@solver
def initialise_environment():
    async def solve(state, generate):
        state.store.set("scenario", copy.deepcopy(state.metadata["scenario"]))
        state.store.set("ordering_account", new_account(state.metadata["scenario"]))
        state.store.set("lab_actions", [])
        state.store.set("experiments", [])
        state.store.set("assays", [])
        state.store.set("service_results", {})
        state.store.set("protocol", "")
        state.store.set("simulation_count", 0)
        return state
    return solve


@tool
def get_environment():
    async def execute() -> str:
        """Read the task inventory, target mixtures, budgets and supported Python/API guide."""
        return json.dumps({"scenario": public_scenario(store().get("scenario")), "ordering": account_summary(store().get("ordering_account")), "api_guide": API_GUIDE}, indent=2)
    return execute


@tool
def write_protocol():
    async def execute(code: str) -> str:
        """Save or replace the full protocol.py in this sample's workspace.

        Args:
            code: Complete Python protocol source, without Markdown fences.
        """
        if not code.strip() or len(code.encode()) > 50000:
            raise ToolError("Supply a nonempty protocol of at most 50 KB")
        store().set("protocol", code)
        store().set("final_validation", None)
        return "Saved protocol.py. Use simulate_protocol to test it; saving does not imply validity."
    return execute


@tool
def read_protocol():
    async def execute() -> str:
        """Read the current saved protocol.py from this sample's workspace."""
        return store().get("protocol", "") or "No protocol saved yet."
    return execute


@tool
def simulate_protocol():
    async def execute() -> str:
        """Test the saved protocol on fresh virtual OT-2 hardware and liquid inventory."""
        scenario = store().get("scenario")
        action_count = len(store().get("lab_actions", []))
        count = store().get("simulation_count", 0)
        if count >= scenario["max_simulations"]:
            raise ToolError("Simulation budget exhausted; final grading still independently runs")
        code = store().get("protocol", "")
        if not code:
            raise ToolError("Write a protocol first")
        store().set("simulation_count", count + 1)
        if store().get("ordering_account") is not None:
            report = await validate_code(code, scenario["id"], inventory=scenario)
        else:
            report = await validate_code(code, scenario["id"])
        if scenario.get("failure_modes"):
            from src.failures import fingerprint
            experiments = copy.deepcopy(store().get("experiments", []))
            experiment = {"id": f"experiment-{len(experiments) + 1:04d}",
                          "protocol_sha256": hashlib.sha256(code.encode()).hexdigest(),
                          "inventory_sha256": fingerprint(scenario),
                          "scenario": copy.deepcopy(scenario), "report": copy.deepcopy(report),
                          "action_count": action_count}
            experiments.append(experiment)
            store().set("experiments", experiments)
        store().set("last_simulation", report)
        # Full evidence remains in the Inspect store; feedback is small.
        feedback = {key: value for key, value in report.items() if key not in ("events", "opentrons_commands", "sdk_diagnostics")}
        if scenario.get("failure_modes"):
            from src.failures import public_feedback
            feedback = public_feedback(report)
            feedback["experiment_id"] = experiment["id"]
        feedback["simulations_remaining"] = scenario["max_simulations"] - count - 1
        return json.dumps(feedback, indent=2)
    return execute


@tool
def list_catalogue():
    async def execute() -> str:
        """List simulated order items, prices in cents, pack sizes and remaining budget."""
        if store().get("ordering_account") is None:
            raise ToolError("Ordering is not enabled for this task")
        catalogue = get_catalogue()
        scenario = store().get("scenario")
        components = {component for source in scenario["sources"].values() for component in source["components"]}
        catalogue["items"] = {name: item for name, item in catalogue["items"].items() if (item["category"] == "reagent" and item["component"] in components and (item["component"] not in scenario.get("sequence_inventory", {}) or item.get("sequence") == scenario["sequence_inventory"][item["component"]])) or (item["category"] == "consumable" and item["load_name"] in scenario["labware"].values())}
        return json.dumps({"catalogue": catalogue, "account": account_summary(store().get("ordering_account"))}, indent=2)
    return execute


@tool
def order_supplies():
    async def execute(item_id: str, destination: str, quantity: int = 1, replace: bool = False, request_id: str = "") -> str:
        """Purchase and immediately deliver simulated supplies within the task budget.

        Args:
            item_id: Exact item ID from list_catalogue.
            destination: Configured source well such as 1:A1 for reagent delivery; deck slot such as 2 for tips or 3 for a plate.
            quantity: Number of reagent aliquots, from 1 to 10. Consumables must be ordered one at a time.
            replace: Discard existing stock or consumable before delivery, with no refund. Required to replace a failed reagent lot.
            request_id: Optional retry ID; identical retries return the receipt without charging again. Different arguments cannot reuse the ID.
        """
        try:
            scenario, account, receipt = place_order(store().get("scenario"), store().get("ordering_account"), item_id, destination, quantity, replace, request_id)
        except OrderError as exc:
            raise ToolError(str(exc)) from exc
        if scenario.get("failure_modes"):
            actions = copy.deepcopy(store().get("lab_actions", []))
            actions.append({"kind": "order", "request": receipt["request"]})
            store().set("lab_actions", actions)
        store().set("scenario", scenario)
        store().set("ordering_account", account)
        store().set("final_validation", None)
        return json.dumps(receipt, indent=2)
    return execute


@tool
def read_sequence():
    async def execute(item_id: str) -> str:
        """Read a validated DNA input belonging to this task, from single- or multi-record FASTA.

        Args:
            item_id: DNA catalogue ID (e.g. gibson_backbone or fragment_001), or the task's DNA component name.
        """
        from src.fragments import read_sequence_metadata
        permitted = (store().get("scenario") or {}).get("sequence_inventory", {})
        if not permitted:
            raise ToolError("Sequence is not part of this task's inventory")
        metadata = permitted.get(item_id)
        if metadata is None:
            item = get_catalogue()["items"].get(item_id, {})
            metadata = permitted.get(item.get("component"))
            if metadata is None or item.get("sequence") != metadata:
                raise ToolError("Sequence is not part of this task's inventory")
        try:
            sequence = read_sequence_metadata(metadata)
        except (ValueError, KeyError, OSError) as exc:
            raise ToolError(str(exc)) from exc
        return json.dumps({"metadata": metadata, "sequence": sequence, "assembly_design": metadata.get("assembly_design", "not_provided; exact adjacent source partition")}, indent=2)
    return execute


@tool
def list_human_services():
    async def execute() -> str:
        """List simulated human diagnostic/repair services and their prices."""
        from src.failures import SERVICES
        if not store().get("scenario", {}).get("failure_modes"):
            raise ToolError("Human services are not enabled for this task")
        return json.dumps({"constructed": True, "services": SERVICES, "account": account_summary(store().get("ordering_account"))}, indent=2)
    return execute


@tool
def request_human_service():
    async def execute(service: str, sample: str = "", sample_type: str = "auto", module_slot: str = "4", setpoint_c: float = 50, request_id: str = "") -> str:
        """Pay for a simulated human assay, thermometer measurement, or calibration.

        Args:
            service: run_gel, thermometer_check, or calibrate_temperature. Calibration requires a prior thermometer check.
            sample: For run_gel, a source DNA well or reaction well such as 1:A2 or 4:A1.
            sample_type: auto infers source or reaction from the well address. source tests current stock; reaction tests the latest simulation even if inventory has since changed.
            module_slot: Configured module slot for thermometer or calibration services.
            setpoint_c: Requested thermometer setpoint in Celsius, between 4 and 95.
            request_id: Optional idempotency key. Identical retries return the original observation without another charge; use a new key for a new measurement.
        """
        from src.failures import gel_assay, human_service
        scenario, account = store().get("scenario"), store().get("ordering_account")
        if sample_type == "auto":
            sample_type = "source" if sample in scenario["sources"] else "reaction"
        try:
            updated, charged, receipt = human_service(scenario, account, service, sample, sample_type, module_slot, setpoint_c, request_id)
            cache = copy.deepcopy(store().get("service_results", {}))
            if receipt["service_id"] in cache:
                return json.dumps(cache[receipt["service_id"]], indent=2)
            if service == "run_gel":
                experiments = store().get("experiments", [])
                experiment = experiments[-1] if experiments and sample_type == "reaction" else None
                assay = gel_assay(scenario, sample, sample_type, experiment=experiment)
                assay["service_id"] = receipt["service_id"]
                assay["action_count"] = len(store().get("lab_actions", [])) + 1
                receipt["result"]["assay"] = assay
            else:
                assay = None
        except (OrderError, KeyError, TypeError) as exc:
            return json.dumps({"error": str(exc), "charged": False, "hint": "Supply a valid sample well for gels; auto infers a stock or reaction lane. Use a new request_id for each new measurement."})
        charged["human_services"][-1] = copy.deepcopy(receipt)
        actions = copy.deepcopy(store().get("lab_actions", []))
        actions.append({"kind": "human_service", "request": receipt["request"]})
        cache[receipt["service_id"]] = copy.deepcopy(receipt)
        if assay:
            assays = copy.deepcopy(store().get("assays", []))
            assays.append(assay)
            store().set("assays", assays)
        store().set("scenario", updated)
        store().set("ordering_account", charged)
        store().set("lab_actions", actions)
        store().set("service_results", cache)
        store().set("final_validation", None)
        return json.dumps(receipt, indent=2)
    return execute
