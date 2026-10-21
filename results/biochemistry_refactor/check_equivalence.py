"""Compare full reports against the saved pre-refactor implementation.

Uses existing real rollout evidence plus explicitly constructed counterexamples.
No model API call or unrestricted execution of model-generated code occurs.
"""
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from Bio import SeqIO
from Bio.Seq import Seq
from src import biochemistry
from src.scenarios import get_scenario

DIRECTORY = Path(__file__).resolve().parent
module_spec = importlib.util.spec_from_file_location("before_refactor", DIRECTORY / "source_before.py")
before = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(before)

scenario = get_scenario("gibson_assembly")
evidence_path = ROOT / "results/biochemistry/final_model_replay/evidence.json"
evidence = json.loads(evidence_path.read_text())
results = []


def compare(name, task, simulation, *, origin="constructed counterexample"):
    expected = before.evaluate_biochemistry(copy.deepcopy(task), copy.deepcopy(simulation))
    actual = biochemistry.evaluate_biochemistry(copy.deepcopy(task), copy.deepcopy(simulation))
    identical = actual == expected
    item = {
        "case": name,
        "origin": origin,
        "identical": identical,
        "before_report_sha256": hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest(),
        "after_report_sha256": hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest(),
    }
    if not identical:
        item.update(before=expected, after=actual)
    results.append(item)


def mutate_path(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


compare("saved_actual_rollout_evidence", scenario, evidence, origin=str(evidence_path.relative_to(ROOT)))
compare("no_biochemical_profile", get_scenario("two_reagent_mix"), evidence)
for profile_path, replacements in [
    (("model",), ["unsupported"]),
    (("topology",), ["linear"]),
    (("sequence_file",), ["../outside-repo.fasta", "missing.fasta"]),
    (("expected_product_id",), ["missing"]),
    (("assembly_order",), [[], ["backbone", "backbone"], ["insert_A", "insert_B"]]),
    (("reaction_wells",), [[], ["3:A1"]]),
    (("dna", "backbone", "orientation"), ["?", "-"]),
    (("dna", "backbone", "linear"), [False]),
    (("dna", "backbone", "purified"), [False]),
    (("dna", "backbone", "concentration_ng_ul"), [0, -1, True, "50"]),
    (("dna", "insert_A", "concentration_ng_ul"), [15, 300]),
    (("master_mix", "active"), [False, None]),
    (("master_mix", "component"), ["backbone"]),
    (("master_mix", "stock_concentration_x"), [0, 1, -1]),
    (("criteria", "overlap_bp"), [[0, 30], [20.0, 30.0], [20, 201]]),
    (("criteria", "total_dna_pmol"), [[0.5, 0.02], [0.1], [0, 0]]),
    (("criteria", "dsdna_g_mol_per_bp"), [0, -1]),
    (("criteria", "reaction_volume_ul"), [0, 21]),
    (("criteria", "volume_tolerance_ul"), [-1]),
]:
    for replacement in replacements:
        changed = copy.deepcopy(scenario)
        mutate_path(changed["biochemistry"], profile_path, replacement)
        compare("profile." + ".".join(profile_path) + "=" + repr(replacement), changed, evidence)

for component in ("backbone", "insert_A", "insert_B", "gibson_master_mix", "water", "unknown"):
    for volume_ul in (0, 0.5, 5, -1, "invalid"):
        changed = copy.deepcopy(evidence)
        changed["final_wells"]["4:A1"][component] = volume_ul
        compare(f"volume.{component}={volume_ul!r}", scenario, changed)

for field, replacements in [
    ("seconds", [0, 899, 900, 3600, 3601, -1, "invalid"]),
    ("temperature_c", [37, 49.5, 50, 50.5, 60, -1, "invalid"]),
    ("mixed", [False, None]),
    ("revision", [-1, None]),
    ("components_ul", [{}, {"water": 1}]),
]:
    for replacement in replacements:
        changed = copy.deepcopy(evidence)
        event = next(event for event in changed["events"] if event["action"] == "incubate")
        event[field] = replacement
        compare(f"incubation.{field}={replacement!r}", scenario, changed)

for field, replacement in [
    ("events", []), ("final_wells", {}), ("well_revisions", {}),
    ("liquid_handling_passed", False),
]:
    changed = copy.deepcopy(evidence)
    changed[field] = replacement
    compare(f"evidence.{field}={replacement!r}", scenario, changed)

changed = copy.deepcopy(evidence)
incubation = next(event for event in changed["events"] if event["action"] == "incubate")
incubation["seconds"] = 1800
changed["events"].append(copy.deepcopy(incubation))
compare("cumulative_incubation", scenario, changed)

changed = copy.deepcopy(evidence)
changed["events"] = []
changed["well_revisions"] = None
compare("no_incubation_does_not_read_revision_mapping", scenario, changed)

# Sequence controls use temporary constructed FASTA inputs; never modify real inputs.
sequence_path = ROOT / scenario["biochemistry"]["sequence_file"]
with tempfile.TemporaryDirectory() as directory:
    temporary_root = Path(directory)
    try:
        for mutation in ("internal_base", "ambiguous_ends", "duplicate_id", "ambiguous_base"):
            records = list(SeqIO.parse(sequence_path, "fasta"))
            for record in records:
                if mutation == "internal_base" and record.id == "insert_A":
                    sequence = str(record.seq)
                    record.seq = Seq(sequence[:100] + ("A" if sequence[100] != "A" else "C") + sequence[101:])
                elif mutation == "ambiguous_ends" and record.id in scenario["biochemistry"]["dna"]:
                    record.seq = Seq("A" * len(record))
                elif mutation == "ambiguous_base" and record.id == "insert_A":
                    record.seq = Seq("N" + str(record.seq)[1:])
            if mutation == "duplicate_id":
                records.append(records[0])
            SeqIO.write(records, temporary_root / "sequences.fasta", "fasta")
            changed = copy.deepcopy(scenario)
            changed["biochemistry"]["sequence_file"] = "sequences.fasta"
            before.ROOT = biochemistry.ROOT = temporary_root
            compare("sequence." + mutation, changed, evidence)
    finally:
        before.ROOT = biochemistry.ROOT = ROOT

record = {
    "command": ".venv/bin/python results/biochemistry_refactor/check_equivalence.py",
    "model": "No new model generation; saved Kimi K3 evidence plus constructed mutations",
    "configuration": "Compare entire report dictionaries, including check order, values, basis text and errors",
    "python": platform.python_version(),
    "biopython": importlib.metadata.version("biopython"),
    "before_source_sha256": hashlib.sha256((DIRECTORY / "source_before.py").read_bytes()).hexdigest(),
    "after_source_sha256": hashlib.sha256((ROOT / "src/biochemistry.py").read_bytes()).hexdigest(),
    "evidence_sha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    "sequence_file_sha256": hashlib.sha256(sequence_path.read_bytes()).hexdigest(),
    "scenario_sha256": hashlib.sha256(json.dumps(scenario, sort_keys=True).encode()).hexdigest(),
    "case_count": len(results),
    "passed": all(item["identical"] for item in results),
    "cases": results,
}
(DIRECTORY / "equivalence.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"passed": record["passed"], "case_count": len(results)}))
raise SystemExit(0 if record["passed"] else 1)
