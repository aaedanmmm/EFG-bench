"""Constructed purchasing fixtures plus real SDK and biochemical-gate validation."""
import asyncio
from importlib import import_module
import copy
import json
from types import SimpleNamespace
import pytest
from inspect_ai.scorer import CORRECT, INCORRECT, Target
from inspect_ai.tool import ToolError
from inspect_ai.util import Store
from src import environment, ordering
from src.costs import get_catalogue
ot2_biochemistry_ordering = import_module("src.abc-2").ot2_biochemistry_ordering
from src.ordering import OrderError, new_account, place_order, replay_orders
from src.runner import validate_code
from src.scenarios import ROOT, get_scenario
from src.scorer import ot2_mixture

REFERENCE = (ROOT / "examples/gibson_assembly.py").read_text()
REQUESTS = [("gibson_backbone","1:A1"),("gibson_insert_A","1:A2"),("gibson_insert_B","1:A3"),("gibson_master_mix","1:A4"),("nuclease_free_water","1:A5"),("filtered_tips_20ul","2"),("temperature_reaction_plate","4")]


def prepared():
    scenario = get_scenario("gibson_order_supplies")
    account = new_account(scenario)
    for item, destination in REQUESTS:
        scenario, account, _ = place_order(scenario, account, item, destination)
    return scenario, account


def set_workspace(monkeypatch, scenario):
    workspace = Store({"scenario":scenario,"ordering_account":new_account(scenario)})
    monkeypatch.setattr(environment,"store",lambda:workspace)
    return workspace


def test_biochemical_catalogue_uses_its_own_sequences(monkeypatch):
    scenario = get_scenario("gibson_order_supplies")
    set_workspace(monkeypatch,scenario)
    items = json.loads(asyncio.run(environment.list_catalogue()()))["catalogue"]["items"]
    assert set(items) == {item for item, _ in REQUESTS}
    assert "backbone" not in items  # Supplied genomic remainder is a different item.
    assert "expected_product" not in items
    assert items["gibson_backbone"]["sequence"] == scenario["sequence_inventory"]["backbone"]
    assert [items[name]["concentration_ng_per_ul"] for name in ("gibson_backbone","gibson_insert_A","gibson_insert_B")] == [50,30,40]


def test_single_record_and_multirecord_backbones_cannot_be_substituted():
    scenario = get_scenario("gibson_order_supplies")
    with pytest.raises(OrderError, match="Sequence identity"):
        place_order(scenario,new_account(scenario),"backbone","1:A1")
    from src.fragments import ordering_scenario
    partitions = ordering_scenario()
    with pytest.raises(OrderError, match="Sequence identity"):
        place_order(partitions,new_account(partitions),"gibson_backbone","1:B1")


def test_biochemistry_sequence_tool_reads_the_correct_fasta_record(monkeypatch):
    scenario = get_scenario("gibson_order_supplies")
    set_workspace(monkeypatch,scenario)
    by_item=json.loads(asyncio.run(environment.read_sequence()("gibson_backbone")))
    by_component=json.loads(asyncio.run(environment.read_sequence()("backbone")))
    assert by_item == by_component
    assert len(by_item["sequence"]) == 1000
    assert by_item["metadata"]["sequence_file"] == "data/biochemistry/synthetic_gibson.fasta"
    with pytest.raises(ToolError,match="not part"):
        asyncio.run(environment.read_sequence()("fragment_001"))


@pytest.mark.parametrize("item,field,value,error", [
    ("gibson_backbone","concentration_ng_per_ul",20,"DNA stock concentration"),
    ("gibson_master_mix","stock_concentration_x",1,"Master-mix concentration"),
])
def test_wrong_stock_properties_rejected_atomically(monkeypatch,item,field,value,error):
    scenario=get_scenario("gibson_order_supplies")
    catalogue=get_catalogue();catalogue["items"][item][field]=value
    monkeypatch.setattr(ordering,"get_catalogue",lambda:copy.deepcopy(catalogue))
    account=new_account(scenario)
    destination="1:A1" if item=="gibson_backbone" else "1:A4"
    with pytest.raises(OrderError,match=error):
        place_order(scenario,account,item,destination)
    assert account["spent_cents"] == 0


def test_deliveries_preserve_dna_concentrations_and_mix_strength():
    scenario, account = prepared()
    assert account["spent_cents"] == 66650
    assert account["budget_cents"] - account["spent_cents"] == 3350
    assert scenario["sources"]["1:A4"]["stock_concentration_x"] == 2
    for well,name,concentration in [("1:A1","backbone",50),("1:A2","insert_A",30),("1:A3","insert_B",40)]:
        assert scenario["sources"][well]["sequence"] == scenario["sequence_inventory"][name]
        assert scenario["sources"][well]["concentration_ng_per_ul"] == concentration
    assert replay_orders(get_scenario("gibson_order_supplies"),account["orders"]) == (scenario,account)


@pytest.fixture(scope="module")
def valid_result():
    scenario,account=prepared()
    state=SimpleNamespace(metadata={"scenario":get_scenario("gibson_order_supplies")},store=Store({"protocol":REFERENCE,"ordering_account":account}))
    result=asyncio.run(ot2_mixture()(state,Target("")))
    assert result.value == CORRECT,result.explanation
    return result


def test_order_to_liquid_handling_and_biochemistry_pipeline(valid_result):
    data=valid_result.metadata
    assert data["score_breakdown"] == {"overall":1,"liquid_handling":1,"biochemistry":1}
    assert len(data["biochemistry"]["checks"]) == 21
    assert all(check["passed"] for check in data["biochemistry"]["checks"])
    assert data["biochemistry"]["experimental_status"] == "not_measured"
    assert data["ordering"]["spent_cents"] == 66650
    assert len(data["ordering"]["orders"]) == 7
    assert data["tips_used"] == 5


def test_unpurchased_module_labware_cannot_be_loaded():
    scenario,account=prepared()
    original=get_scenario("gibson_order_supplies")
    without_plate=[order for order in account["orders"] if order["request"]["item_id"] != "temperature_reaction_plate"]
    missing,_=replay_orders(original,without_plate)
    result=asyncio.run(validate_code(REFERENCE,missing["id"],inventory=missing))
    assert not result["passed"]
    assert "Module labware" in " ".join(result["errors"])


def test_purchasing_alone_does_not_bypass_biochemical_gates():
    scenario,account=prepared()
    wrong=REFERENCE.replace("temperature.set_temperature(50)","temperature.set_temperature(25)")
    result=asyncio.run(validate_code(wrong,scenario["id"],inventory=scenario))
    assert result["liquid_handling_passed"]
    assert not result["passed"]
    assert not result["biochemistry"]["passed"]


def test_existing_preloaded_biochemical_task_can_restock():
    scenario=get_scenario("gibson_assembly")
    updated,account,_=place_order(scenario,new_account(scenario),"gibson_backbone","1:A1")
    assert updated["sources"]["1:A1"]["components"]["backbone"] == 150
    assert account["spent_cents"] == 15000


def test_ordering_task_is_runnable():
    task=ot2_biochemistry_ordering()
    assert [s.id for s in task.dataset] == ["sequence_assembly_order_supplies"]
    assert task.message_limit == 60
