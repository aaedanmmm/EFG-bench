"""Pure, atomic state transitions for simulated ordering; no external purchases.

Money is integer cents. Orders persist between dry-run simulations. The scorer
replays accepted requests against the original scenario to reconstruct inventory.
"""
import copy
import json
from src.costs import get_catalogue


class OrderError(ValueError):
    pass


def new_account(scenario):
    config = scenario.get("ordering")
    if not config:
        return None
    return {"budget_cents": config["budget_cents"], "spent_cents": 0, "orders": []}


def public_scenario(scenario):
    result = copy.deepcopy(scenario)
    if "ordering" in result:
        result["ordering"].pop("faulty_lots", None)
    for source in result["sources"].values():
        source.pop("usable", None)
    return result


def account_summary(account):
    if account is None:
        return None
    return {"currency": "USD", "budget_cents": account["budget_cents"], "spent_cents": account["spent_cents"], "remaining_cents": account["budget_cents"] - account["spent_cents"], "orders": copy.deepcopy(account["orders"])}


def place_order(original, account, item_id, destination, quantity=1, replace=False, request_id=""):
    """Validate everything before committing; return new inventory/account/receipt.

    Retrying a request_id with the same arguments returns its prior receipt.
    A conflicting retry fails. Replacement discards previous stock without refund.
    """
    if account is None or "ordering" not in original:
        raise OrderError("Ordering is not enabled for this task")
    if type(quantity) is not int or not 1 <= quantity <= 10:
        raise OrderError("Quantity must be an integer from 1 to 10")
    if type(replace) is not bool:
        raise OrderError("replace must be a boolean")
    if not isinstance(destination, str) or len(destination) > 30:
        raise OrderError("Destination must be a source well (e.g. 1:A1) or deck slot (e.g. 2)")
    if not isinstance(request_id, str) or len(request_id) > 80:
        raise OrderError("request_id must be text of at most 80 characters")
    catalogue = get_catalogue()
    if item_id not in catalogue["items"]:
        raise OrderError(f"Unknown catalogue item: {item_id}")
    request = {"item_id": item_id, "destination": destination, "quantity": quantity, "replace": replace, "request_id": request_id}
    if request_id:
        for prior in account["orders"]:
            if prior["request"]["request_id"] == request_id:
                if prior["request"] != request:
                    raise OrderError("request_id already belongs to a different order")
                return copy.deepcopy(original), copy.deepcopy(account), copy.deepcopy(prior)
    item = catalogue["items"][item_id]
    cost = item["price_cents"] * quantity
    if account["spent_cents"] + cost > account["budget_cents"]:
        raise OrderError(f"Insufficient budget: order costs {cost} cents, remaining {account['budget_cents'] - account['spent_cents']} cents")
    scenario, updated = copy.deepcopy(original), copy.deepcopy(account)
    order_id = f"order-{len(updated['orders']) + 1:04d}"
    previous = None
    if item["category"] == "reagent":
        source = scenario["sources"].get(destination)
        if source is None:
            raise OrderError("Deliver reagents only to source wells listed in the task")
        if set(source["components"]) != {item["component"]}:
            raise OrderError("This source well is assigned to a different reagent")
        capacities = scenario["ordering"]["source_capacity_ul"]
        current_volume = sum(source["components"].values())
        delivered = item["volume_ul"] * quantity
        if (0 if replace else current_volume) + delivered > capacities[destination]:
            raise OrderError(f"Delivery exceeds source capacity of {capacities[destination]} uL")
        if current_volume > 0 and not source.get("usable", True) and not replace:
            raise OrderError("Replace the failed lot; topping up would retain the failed stock")
        lot_number = 1 + sum(order["request"]["item_id"] == item_id for order in updated["orders"])
        usable = lot_number not in scenario["ordering"].get("faulty_lots", {}).get(item_id, [])
        previous = {"components": dict(source["components"]), "lot_id": source.get("lot_id")} if replace else None
        source["components"][item["component"]] = (0 if replace else current_volume) + delivered
        # A failed delivery cannot be repaired by blending it with a good lot.
        source["usable"] = usable and (replace or source.get("usable", True))
        source["lot_id"] = order_id
        delivery = {"source_well": destination, "component": item["component"], "volume_ul": delivered, "lot_id": order_id, "quality": "unverified"}
    else:
        if quantity != 1:
            raise OrderError("One consumable occupies one slot; order one at a time")
        if scenario["labware"].get(destination) != item["load_name"]:
            raise OrderError("Consumable does not match the configured labware in that slot")
        unavailable = scenario.get("unavailable_labware_slots", [])
        if destination not in unavailable and not replace:
            raise OrderError("Slot is occupied; use replace=true to discard and replace that consumable")
        if destination in unavailable:
            unavailable.remove(destination)
        if "tip_count" in item:
            if destination not in scenario["pipette"]["tip_slots"]:
                raise OrderError("This is not a configured tip rack slot")
            scenario.setdefault("available_tips", {})[destination] = item["tip_count"]
        else:
            # Protocols are dry runs; plates are empty in the planning inventory.
            if any(key.split(":")[0] == destination and sum(source["components"].values()) > 0 for key, source in scenario["sources"].items()):
                raise OrderError("Cannot replace labware containing source stock")
        delivery = {"slot": destination, "load_name": item["load_name"]}
        if "tip_count" in item:
            delivery["available_tips"] = item["tip_count"]
    updated["spent_cents"] += cost
    receipt = {"order_id": order_id, "request": request, "status": "delivered", "currency": catalogue["currency"], "total_cents": cost, "remaining_cents": updated["budget_cents"] - updated["spent_cents"], "delivery": delivery}
    if previous is not None:
        receipt["discarded_stock"] = previous
    updated["orders"].append(receipt)
    return scenario, updated, copy.deepcopy(receipt)


def replay_orders(original, orders):
    """Reconstruct inventory and charges using trusted catalogue/config, not receipts."""
    scenario = copy.deepcopy(original)
    account = new_account(original)
    if account is None:
        if orders:
            raise OrderError("Orders supplied for a task without ordering")
        return scenario, None
    for receipt in orders:
        scenario, account, _ = place_order(scenario, account, **receipt["request"])
    return scenario, account
