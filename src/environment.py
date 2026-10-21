"""Sample-scoped agent workspace. Tools never execute arbitrary agent Python."""
import copy
import json
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

Ordering tasks also expose list_catalogue and order_supplies. All purchases are
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
It does not model reaction success, kinetics, liquid height, pipetting error,
residual film quantities, or biological activity. No physical robot is used.
""".strip()


@solver
def initialise_environment():
    async def solve(state, generate):
        state.store.set("scenario", copy.deepcopy(state.metadata["scenario"]))
        state.store.set("ordering_account", new_account(state.metadata["scenario"]))
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
        store().set("last_simulation", report)
        # Full evidence remains in the Inspect store; feedback is small.
        feedback = {key: value for key, value in report.items() if key not in ("events", "opentrons_commands", "sdk_diagnostics")}
        feedback["simulations_remaining"] = scenario["max_simulations"] - count - 1
        return json.dumps(feedback, indent=2)
    return execute


@tool
def list_catalogue():
    async def execute() -> str:
        """List simulated order items, prices in cents, pack sizes and remaining budget."""
        if store().get("ordering_account") is None:
            raise ToolError("Ordering is not enabled for this task")
        return json.dumps({"catalogue": get_catalogue(), "account": account_summary(store().get("ordering_account"))}, indent=2)
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
        store().set("scenario", scenario)
        store().set("ordering_account", account)
        store().set("final_validation", None)
        return json.dumps(receipt, indent=2)
    return execute
