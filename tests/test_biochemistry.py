"""Biochemical model tests. Mutated states are constructed counterexamples.

The base evidence is produced by real SDK simulation. Perturbing a copied state
here tests acceptance gates, and does not represent a wet-lab observation.
"""
import asyncio
import copy
from pathlib import Path
import pytest
from Bio import SeqIO
from src import biochemistry
from src.biochemistry import circular_equal, evaluate_biochemistry
from src.runner import validate_code
from src.scenarios import get_scenario

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (ROOT / "examples/gibson_assembly.py").read_text()


@pytest.fixture(scope="module")
def baseline():
    result = asyncio.run(validate_code(REFERENCE, "gibson_assembly"))
    assert result["passed"], result["errors"]
    return result


def ids(report):
    return {item["id"] for item in report["checks"] if not item["passed"]}


def test_reference_formula_product_and_experimental_label(baseline):
    bio = baseline["biochemistry"]
    assert len(bio["checks"]) == 21
    assert bio["passed"]
    assert bio["experimental_status"] == "not_measured"
    assert len(bio["assembly"]["predicted_sequence"]) == 2340
    reaction = bio["reactions"][0]
    assert reaction["master_mix_final_x"] == 1
    assert reaction["dna"]["backbone"]["pmol"] == pytest.approx(50 * 1000 / (1000 * 650))
    assert reaction["total_dna_pmol"] == pytest.approx(0.3846153846)
    assert reaction["insert_backbone_ratios"] == {"insert_A": 2, "insert_B": 2}
    assert reaction["qualified_incubation_seconds"] == 3600


def test_no_biochemistry_spec_is_not_biochemical_success(baseline):
    result = evaluate_biochemistry(get_scenario("two_reagent_mix"), baseline)
    assert result["status"] == "not_applicable"
    assert result["passed"] is None


@pytest.mark.parametrize("field,value,failed", [
    ("active", False, "enzyme.active"),
    ("stock_concentration_x", 1, "4:A1.master_mix_concentration"),
])
def test_master_mix_properties(baseline, field, value, failed):
    scenario = get_scenario("gibson_assembly")
    scenario["biochemistry"]["master_mix"][field] = value
    result = evaluate_biochemistry(scenario, baseline)
    assert failed in ids(result)


def test_wrong_molar_ratio_with_correct_liquid_volumes(baseline):
    scenario = get_scenario("gibson_assembly")
    scenario["biochemistry"]["dna"]["insert_A"]["concentration_ng_ul"] *= 0.5
    result = evaluate_biochemistry(scenario, baseline)
    assert "4:A1.molar_ratio.insert_A" in ids(result)
    assert "4:A1.reaction_volume" not in ids(result)


def test_excess_dna_and_non_linear_input(baseline):
    scenario = get_scenario("gibson_assembly")
    for definition in scenario["biochemistry"]["dna"].values():
        definition["concentration_ng_ul"] *= 10
    scenario["biochemistry"]["dna"]["backbone"]["linear"] = False
    result = evaluate_biochemistry(scenario, baseline)
    assert {"4:A1.total_dna", "4:A1.vector_mass", "input.linear_purified_dsdna"} <= ids(result)


def test_missing_dna_and_unmodeled_additive(baseline):
    evidence = copy.deepcopy(baseline)
    del evidence["final_wells"]["4:A1"]["insert_A"]
    evidence["final_wells"]["4:A1"]["unknown_additive"] = 2
    result = evaluate_biochemistry(get_scenario("gibson_assembly"), evidence)
    assert {"4:A1.dna_present.insert_A", "4:A1.reagent_identity"} <= ids(result)


def test_incorrect_sequence_with_correct_size_is_rejected(baseline, monkeypatch, tmp_path):
    scenario = get_scenario("gibson_assembly")
    records = list(SeqIO.parse(ROOT / scenario["biochemistry"]["sequence_file"], "fasta"))
    for record in records:
        if record.id == "insert_A":
            sequence = str(record.seq)
            from Bio.Seq import Seq
            record.seq = Seq(sequence[:100] + ("A" if sequence[100] != "A" else "C") + sequence[101:])
    SeqIO.write(records, tmp_path / "sequences.fasta", "fasta")
    monkeypatch.setattr(biochemistry, "ROOT", tmp_path)
    scenario["biochemistry"]["sequence_file"] = "sequences.fasta"
    result = evaluate_biochemistry(scenario, baseline)
    assert "product.sequence_identity" in ids(result)
    assert not any(name.endswith(".homology") for name in ids(result))
    assert len(result["assembly"]["predicted_sequence"]) == 2340


def test_reversed_fragment_has_incompatible_junctions(baseline):
    scenario = get_scenario("gibson_assembly")
    scenario["biochemistry"]["dna"]["insert_A"]["orientation"] = "-"
    result = evaluate_biochemistry(scenario, baseline)
    assert not result["passed"]
    assert "junction.backbone->insert_A.homology" in ids(result)
    assert "product.sequence_identity" in ids(result)


def test_ambiguous_self_joining_rejected(baseline, monkeypatch, tmp_path):
    scenario = get_scenario("gibson_assembly")
    records = list(SeqIO.parse(ROOT / scenario["biochemistry"]["sequence_file"], "fasta"))
    from Bio.Seq import Seq
    for record in records:
        if record.id in ("backbone", "insert_A", "insert_B"):
            record.seq = Seq("A" * len(record))
    SeqIO.write(records, tmp_path / "sequences.fasta", "fasta")
    monkeypatch.setattr(biochemistry, "ROOT", tmp_path)
    scenario["biochemistry"]["sequence_file"] = "sequences.fasta"
    result = evaluate_biochemistry(scenario, baseline)
    assert "junction.backbone.specificity" in ids(result)


@pytest.mark.parametrize("mutation", ["none", "too_short", "wrong_temperature", "before_mixing", "stale_revision"])
def test_incubation_gate(baseline, mutation):
    evidence = copy.deepcopy(baseline)
    event = next(event for event in evidence["events"] if event["action"] == "incubate")
    if mutation == "none":
        evidence["events"] = []
    elif mutation == "too_short":
        event["seconds"] = 899
    elif mutation == "wrong_temperature":
        event["temperature_c"] = 37
    elif mutation == "before_mixing":
        event["mixed"] = False
    else:
        event["revision"] -= 1
    result = evaluate_biochemistry(get_scenario("gibson_assembly"), evidence)
    assert "4:A1.incubation" in ids(result)


def test_liquid_handling_failure_cannot_pass_biochemistry(baseline):
    evidence = copy.deepcopy(baseline)
    evidence["liquid_handling_passed"] = False
    assert "execution.liquid_handling" in ids(evaluate_biochemistry(get_scenario("gibson_assembly"), evidence))


def test_bad_profile_fails_closed(baseline):
    scenario = get_scenario("gibson_assembly")
    scenario["biochemistry"]["criteria"]["total_dna_pmol"] = [0.5, 0.02]
    assert "configuration.valid" in ids(evaluate_biochemistry(scenario, baseline))


def test_circular_identity_accounts_for_rotation_and_reverse_complement():
    from Bio.Seq import Seq
    sequence = "AAACCGTCTAGT"
    assert circular_equal(sequence, sequence[4:] + sequence[:4])
    assert circular_equal(sequence, str(Seq(sequence).reverse_complement()))
    assert not circular_equal(sequence, "AAACCGTCTAGA")


@pytest.mark.parametrize("replacement", ["", "    protocol.delay(minutes=1)\n"])
def test_real_protocol_without_enough_incubation_fails(replacement):
    code = REFERENCE.replace("    protocol.delay(minutes=60)\n", replacement)
    result = asyncio.run(validate_code(code, "gibson_assembly"))
    assert result["liquid_handling_passed"]
    assert not result["passed"]
    assert "4:A1.incubation" in ids(result["biochemistry"])


def test_real_protocol_heated_before_adding_dna_fails():
    heating = "    temperature.set_temperature(50)\n    protocol.delay(minutes=60)\n"
    code = REFERENCE.replace(heating, "")
    code = code.replace('    pipette.transfer(1, stock["A1"], plate["A1"])', heating + '    pipette.transfer(1, stock["A1"], plate["A1"])')
    result = asyncio.run(validate_code(code, "gibson_assembly"))
    assert result["liquid_handling_passed"]
    assert not result["passed"]


def test_review_is_auditable_and_marks_unmeasured_outcome(baseline, tmp_path):
    from src.review import write_review
    path = write_review(baseline, tmp_path, origin="constructed test fixture")
    text = path.read_text()
    assert "Experimental outcome: NOT MEASURED" in text
    assert "4:A1.incubation" in text
    assert "50 C for 3600 seconds" in text
    assert "0.384615" in text
    assert (tmp_path / "evidence.json").is_file()
    assert (tmp_path / "predicted_product.fasta").is_file()


def test_fresh_scorer_rejects_correct_pipetting_without_biochemistry():
    from types import SimpleNamespace
    from inspect_ai.scorer import INCORRECT, Target
    from inspect_ai.util import Store
    from src.scorer import ot2_mixture
    code = REFERENCE.replace("    protocol.delay(minutes=60)\n", "")
    state = SimpleNamespace(metadata={"scenario": get_scenario("gibson_assembly")}, store=Store({"protocol": code, "last_simulation": {"passed": True}}))
    score = asyncio.run(ot2_mixture()(state, Target("")))
    assert score.value == INCORRECT
    assert score.metadata["score_breakdown"] == {"overall": 0, "liquid_handling": 1, "biochemistry": 0}
    assert score.metadata["tip_efficiency"] == 0
    assert "4:A1.incubation" in score.explanation


def test_incubation_matching_tolerates_ledger_serialization_precision(baseline):
    evidence = copy.deepcopy(baseline)
    event = next(event for event in evidence["events"] if event["action"] == "incubate")
    event["components_ul"]["water"] += 1e-9
    result = evaluate_biochemistry(get_scenario("gibson_assembly"), evidence)
    assert result["passed"], ids(result)
