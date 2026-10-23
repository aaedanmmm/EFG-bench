"""FASTA integrity and real SDK ordering integration, using the supplied files."""
import asyncio
import copy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import pytest
from inspect_ai.scorer import CORRECT, Target
from inspect_ai.tool import ToolError
from src import environment, ordering
from src.costs import get_catalogue
from src.fragments import PARTS, SOURCE_FILE, get_fragments, ordering_scenario, sequence_manifest
from src.ordering import OrderError, new_account, place_order, replay_orders
from src.runner import validate_code
from src.scenarios import ROOT
from src.scorer import ot2_mixture
from inspect_ai.util import Store


def supplies():
    scenario = ordering_scenario()
    account = new_account(scenario)
    for well, source in scenario["sources"].items():
        component = next(iter(source["components"]))
        item = "nuclease_free_water" if component == "water" else component
        scenario, account, _ = place_order(scenario, account, item, well)
    for item, slot in [("filtered_tips_20ul", "2"), ("reaction_plate", "3")]:
        scenario, account, _ = place_order(scenario, account, item, slot)
    return scenario, account


def test_supplied_partitions_exactly_reconstruct_source():
    manifest = sequence_manifest()
    assert manifest["source"]["length_bp"] == 12484
    assert manifest["source"]["record_id"] == "ENSG00000164690.8"
    assert manifest["exact_reconstruction"]
    assert list(manifest["fragments"]) == list(PARTS)
    assert [m["length_bp"] for m in manifest["fragments"].values()] == [742,1536,1105,618,1893,1270,5320]
    assert manifest["fragments"]["backbone"]["source_coordinates_1based_inclusive"] == [7165,12484]
    assert "not_provided" in manifest["assembly_design"]


@pytest.fixture
def sequence_copy(tmp_path):
    for path in (ROOT / "data/sequences").glob("*.fasta"):
        shutil.copy(path, tmp_path)
    return tmp_path


def test_changed_bases_rejected(sequence_copy):
    path = sequence_copy / "fragment_001.fasta"
    lines = path.read_text().splitlines()
    lines[1] = ("A" if lines[1][0] != "A" else "C") + lines[1][1:]
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="source coordinates"):
        sequence_manifest(sequence_copy)


def test_missing_part_rejected(sequence_copy):
    (sequence_copy / "backbone.fasta").unlink()
    with pytest.raises(FileNotFoundError):
        sequence_manifest(sequence_copy)


def test_ambiguous_bases_rejected(sequence_copy):
    path = sequence_copy / SOURCE_FILE
    text = path.read_text(); header, seq = text.split("\n", 1)
    path.write_text(header + "\nN" + seq[1:])
    with pytest.raises(ValueError, match="unambiguous"):
        sequence_manifest(sequence_copy)


def test_multiple_records_rejected(sequence_copy):
    path = sequence_copy / "fragment_001.fasta"
    path.write_text(path.read_text() + ">extra\nACGT\n")
    with pytest.raises(ValueError):
        sequence_manifest(sequence_copy)


def test_catalogue_and_delivered_lots_use_same_sequence_identity():
    fragments = get_fragments()
    catalogue = get_catalogue()
    scenario, account = supplies()
    assert account["spent_cents"] == 107250
    assert len(account["orders"]) == 10
    for name in PARTS:
        assert catalogue["items"][name]["sequence"] == fragments[name]
        receipt = next(o for o in account["orders"] if o["request"]["item_id"] == name)
        assert receipt["delivery"]["sequence"]["sha256"] == fragments[name]["sha256"]
        source = scenario["sources"][receipt["delivery"]["source_well"]]
        assert source["sequence"] == fragments[name]
        assert source["concentration_ng_per_ul"] == 20
        assert "not measured" in source["physical_stock_provenance"]
    replayed, replayed_account = replay_orders(ordering_scenario(), account["orders"])
    assert replayed == scenario and replayed_account == account


def test_changed_catalogue_sequence_rejected_before_charging(monkeypatch):
    scenario = ordering_scenario()
    account = new_account(scenario)
    catalogue = get_catalogue()
    catalogue["items"]["fragment_001"]["sequence"]["sha256"] = "wrong"
    monkeypatch.setattr(ordering, "get_catalogue", lambda: copy.deepcopy(catalogue))
    with pytest.raises(OrderError, match="Sequence identity changed"):
        place_order(scenario, account, "fragment_001", "1:A1")
    assert account["spent_cents"] == 0
    assert scenario["sources"]["1:A1"]["components"]["fragment_001"] == 0


def test_read_sequence_returns_exact_input_and_rejects_paths(monkeypatch):
    workspace = Store({"scenario": ordering_scenario()})
    monkeypatch.setattr(environment, "store", lambda: workspace)
    result = json.loads(asyncio.run(environment.read_sequence()("backbone")))
    assert len(result["sequence"]) == 5320
    assert result["metadata"]["record_id"] == "backbone"
    with pytest.raises(ToolError):
        asyncio.run(environment.read_sequence()("../../.env"))


def test_sequence_ordering_and_protocol_pass_real_sdk_and_scorer():
    scenario, account = supplies()
    code = (ROOT / "examples/sequence_partitions.py").read_text()
    state = SimpleNamespace(metadata={"scenario": ordering_scenario()}, store=Store({"protocol":code,"ordering_account":account}))
    result = asyncio.run(ot2_mixture()(state, Target("")))
    assert result.value == CORRECT, result.explanation
    assert result.metadata["final_wells"]["3:A1"] == {**{name:2 for name in PARTS},"water":6}
    assert result.metadata["tips_used"] == 8
    assert result.metadata["sequence_inventory"] == get_fragments()
    assert not result.metadata["biochemistry"]["applicable"]
    assert result.metadata["score_breakdown"]["biochemistry"] is None
    assert result.metadata["ordering"]["spent_cents"] == 107250


def test_generic_tasks_cannot_read_or_export_supplied_sequence_metadata(monkeypatch):
    from src.scenarios import get_scenario
    scenario = get_scenario("order_supplies")
    workspace = Store({"scenario": scenario, "ordering_account": new_account(scenario)})
    monkeypatch.setattr(environment, "store", lambda: workspace)
    catalogue = json.loads(asyncio.run(environment.list_catalogue()()))
    assert not any(name in catalogue["catalogue"]["items"] for name in PARTS)
    assert all("sequence" not in item for item in catalogue["catalogue"]["items"].values())
    with pytest.raises(ToolError, match="not part of this task"):
        asyncio.run(environment.read_sequence()("backbone"))
