"""Constructed order-ledger tests and real SDK inventory integration checks."""
import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from inspect_ai.scorer import CORRECT, INCORRECT, Target
from inspect_ai.tool import ToolError
from inspect_ai.util import Store
from src import environment, ordering
from src.costs import get_catalogue
from src.ordering import OrderError, account_summary, new_account, place_order, public_scenario, replay_orders
from src.runner import validate_code
from src.scenarios import get_scenario
from src.scorer import ot2_mixture

REFERENCE = (Path(__file__).resolve().parents[1] / "examples/two_reagent_mix.py").read_text()
ITEMS = [("reagent_A", "1:A1"), ("nuclease_free_water", "1:A2"), ("filtered_tips_20ul", "2"), ("reaction_plate", "3")]


def prepared(task="order_supplies"):
    scenario = get_scenario(task)
    account = new_account(scenario)
    for item, destination in ITEMS:
        scenario, account, receipt = place_order(scenario, account, item, destination)
    return scenario, account


def test_delivery_receipts_budget_and_original_unchanged():
    original = get_scenario("order_supplies")
    snapshot = copy.deepcopy(original)
    scenario, account = prepared()
    assert original == snapshot
    assert scenario["sources"]["1:A1"]["components"] == {"reagent_A": 100}
    assert scenario["sources"]["1:A2"]["components"] == {"water": 200}
    assert scenario["available_tips"] == {"2": 96}
    assert scenario["unavailable_labware_slots"] == []
    assert account_summary(account)["remaining_cents"] == 250
    assert account["spent_cents"] == 3750
    assert [o["order_id"] for o in account["orders"]] == [f"order-{n:04d}" for n in range(1, 5)]


@pytest.mark.parametrize("item,destination,quantity,replace,error", [
    ("unknown", "1:A1", 1, False, "Unknown"),
    ("reagent_A", "1:A2", 1, False, "different reagent"),
    ("reagent_A", "3:A1", 1, False, "source wells"),
    ("filtered_tips_20ul", "3", 1, False, "does not match"),
    ("reaction_plate", "3", 2, False, "one at a time"),
    ("reagent_A", "1:A1", 0, False, "integer"),
    ("reagent_A", "1:A1", -1, False, "integer"),
    ("reagent_A", "1:A1", True, False, "integer"),
    ("reagent_A", "1:A1", 1.5, False, "integer"),
    ("reagent_A", "1:A1", 1, "true", "boolean"),
    ("reagent_A", "1:A1", 3, False, "Insufficient budget"),
])
def test_rejected_orders_are_atomic(item, destination, quantity, replace, error):
    scenario = get_scenario("order_supplies")
    account = new_account(scenario)
    before = copy.deepcopy((scenario, account))
    with pytest.raises(OrderError, match=error):
        place_order(scenario, account, item, destination, quantity, replace)
    assert (scenario, account) == before


def test_capacity_checked_before_charging():
    scenario = get_scenario("order_supplies")
    scenario["ordering"]["budget_cents"] = 100000
    scenario["ordering"]["source_capacity_ul"]["1:A1"] = 150
    account = new_account(scenario)
    with pytest.raises(OrderError, match="capacity"):
        place_order(scenario, account, "reagent_A", "1:A1", quantity=2)
    assert account["spent_cents"] == 0
    assert scenario["sources"]["1:A1"]["components"]["reagent_A"] == 0


def test_idempotent_retry_and_conflicting_retry():
    scenario = get_scenario("order_supplies")
    scenario, account, first = place_order(scenario, new_account(scenario), "reagent_A", "1:A1", request_id="purchase-A")
    retried, same_account, same_receipt = place_order(scenario, account, "reagent_A", "1:A1", request_id="purchase-A")
    assert retried == scenario and same_account == account and same_receipt == first
    with pytest.raises(OrderError, match="different order"):
        place_order(scenario, account, "reagent_A", "1:A1", quantity=2, request_id="purchase-A")


def test_replacement_discards_stock_and_charges_again():
    scenario = get_scenario("order_supplies")
    scenario["ordering"]["budget_cents"] = 5500
    account = new_account(scenario)
    for item, destination in ITEMS:
        scenario, account, _ = place_order(scenario, account, item, destination)
    scenario, account, receipt = place_order(scenario, account, "reagent_A", "1:A1", replace=True)
    assert account["spent_cents"] == 5250
    assert scenario["sources"]["1:A1"]["components"]["reagent_A"] == 100
    assert receipt["discarded_stock"]["components"]["reagent_A"] == 100


def test_occupied_consumable_requires_explicit_replacement():
    scenario = get_scenario("order_supplies")
    account = new_account(scenario)
    scenario, account, _ = place_order(scenario, account, "reaction_plate", "3")
    with pytest.raises(OrderError, match="occupied"):
        place_order(scenario, account, "reaction_plate", "3")
    scenario, account, _ = place_order(scenario, account, "reaction_plate", "3", replace=True)
    assert account["spent_cents"] == 1400


def test_replay_uses_trusted_prices_and_preserves_inventory():
    scenario, account = prepared()
    orders = copy.deepcopy(account["orders"])
    for receipt in orders:
        receipt["total_cents"] = 0
        receipt["remaining_cents"] = 999999
    replayed, rebuilt = replay_orders(get_scenario("order_supplies"), orders)
    assert rebuilt["spent_cents"] == 3750
    assert replayed == scenario


def test_retired_quality_failure_task_is_not_in_benchmark():
    tasks = json.loads((Path(__file__).resolve().parents[1] / "data/ordering_tasks.json").read_text())
    assert "replace_failed_lot" not in {task["id"] for task in tasks}
    with pytest.raises(ValueError, match="Unknown scenario"):
        get_scenario("replace_failed_lot")
    for suite in ("ordering", "biochemistry", "biochemistry_ordering", "failures"):
        for task in json.loads((Path(__file__).resolve().parents[1] / "data" / f"{suite}_tasks.json").read_text()):
            assert "faulty_lots" not in task.get("ordering", {})
            assert all("usable" not in source for source in task["sources"].values())


def test_missing_supplies_fail_then_ordered_inventory_passes_real_sdk():
    missing = asyncio.run(validate_code(REFERENCE, "order_supplies"))
    assert not missing["passed"]
    assert "unavailable" in " ".join(missing["errors"])
    scenario, account = prepared()
    ready = asyncio.run(validate_code(REFERENCE, "order_supplies", inventory=scenario))
    assert ready["passed"], ready["errors"]
    assert ready["tips_used"] == 4
    assert sum(scenario["sources"]["1:A1"]["components"].values()) == 100  # dry run
    assert account["spent_cents"] == 3750


def test_repeated_replacement_orders_do_not_inject_failures_real_sdk(monkeypatch):
    # Isolate the unrelated invalid genomic partitions; catalogue entries and SDK
    # are real. This does not assert that the current global catalogue loads.
    catalogue = get_catalogue(include_partitions=False)
    monkeypatch.setattr(ordering, "get_catalogue", lambda: copy.deepcopy(catalogue))
    scenario = get_scenario("order_supplies")
    scenario["ordering"]["budget_cents"] = 10000
    account = new_account(scenario)
    for item, destination in ITEMS:
        scenario, account, _ = place_order(scenario, account, item, destination)
    for attempt in range(3):
        ready = asyncio.run(validate_code(REFERENCE, scenario["id"], inventory=scenario))
        assert ready["passed"], ready["errors"]
        assert "usable" not in scenario["sources"]["1:A1"]
        if attempt < 2:
            scenario, account, _ = place_order(scenario, account, "reagent_A", "1:A1", replace=True)


def test_scorer_rebuilds_inventory_and_finances():
    scenario, account = prepared()
    state = SimpleNamespace(metadata={"scenario": get_scenario("order_supplies")}, store=Store({"protocol": REFERENCE, "scenario": {"fake": "inventory"}, "ordering_account": account}))
    result = asyncio.run(ot2_mixture()(state, Target("")))
    assert result.value == CORRECT
    assert result.metadata["ordering"]["spent_cents"] == 3750
    assert result.metadata["cost_efficiency"] == pytest.approx(0.0625)
    # A cached or mutated inventory cannot bypass a missing purchase ledger.
    state.store.set("scenario", scenario)
    state.store.set("ordering_account", {"orders": []})
    failed = asyncio.run(ot2_mixture()(state, Target("")))
    assert failed.value == INCORRECT


def test_order_tool_and_sample_account_isolation(monkeypatch):
    scenario = get_scenario("order_supplies")
    current = Store({"scenario": scenario, "ordering_account": new_account(scenario)})
    monkeypatch.setattr(environment, "store", lambda: current)
    receipt = json.loads(asyncio.run(environment.order_supplies()("reagent_A", "1:A1", request_id="A")))
    assert receipt["total_cents"] == 1500
    assert json.loads(asyncio.run(environment.get_environment()()))["ordering"]["spent_cents"] == 1500
    assert scenario["sources"]["1:A1"]["components"]["reagent_A"] == 0
    new = get_scenario("order_supplies")
    current = Store({"scenario": new, "ordering_account": new_account(new)})
    assert json.loads(asyncio.run(environment.list_catalogue()()))["account"]["spent_cents"] == 0
    with pytest.raises(ToolError):
        asyncio.run(environment.order_supplies()("reagent_A", "1:A1", quantity=-1))
