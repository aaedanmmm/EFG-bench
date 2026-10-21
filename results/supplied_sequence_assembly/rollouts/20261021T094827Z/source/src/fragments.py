"""Read and validate the supplied FASTA partitions without changing their bases.

These are source partitions, not a vector or an assembly-ready overlap design.
Physical aliquot sizes/concentrations used by the eval are benchmark assumptions.
"""
import argparse
import hashlib
import json
from pathlib import Path
from Bio import SeqIO
from src.scenarios import ROOT

SOURCE_FILE = "ENST00000297261.7.fasta"
PARTS = tuple(f"fragment_{index:03d}" for index in range(1, 7)) + ("backbone",)


def read_fasta(path):
    with Path(path).open() as stream:
        record = SeqIO.read(stream, "fasta")
    sequence = str(record.seq).upper()
    if not sequence or set(sequence) - set("ACGT"):
        raise ValueError(f"Expected unambiguous A/C/G/T DNA in {path}")
    return record, sequence


def sequence_manifest(directory=None):
    directory = Path(directory) if directory is not None else ROOT / "data" / "sequences"
    source_path = directory / SOURCE_FILE
    source, original = read_fasta(source_path)
    fragments = {}
    joined = []
    offset = 0
    for name in PARTS:
        path = directory / f"{name}.fasta"
        record, sequence = read_fasta(path)
        if record.id != name:
            raise ValueError(f"FASTA identifier {record.id!r} does not match {name!r}")
        if sequence != original[offset:offset + len(sequence)]:
            raise ValueError(f"Partition {name} does not match its source coordinates")
        fragments[name] = {
            "name": name, "record_id": record.id,
            "sequence_file": f"data/sequences/{path.name}",
            "length_bp": len(sequence),
            "sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source": "user_supplied_sequence_partition",
            "source_coordinates_1based_inclusive": [offset + 1, offset + len(sequence)],
        }
        joined.append(sequence)
        offset += len(sequence)
    if "".join(joined) != original:
        raise ValueError("Fragments and backbone do not exactly reconstruct the source")
    return {
        "source": {"sequence_file": f"data/sequences/{SOURCE_FILE}", "record_id": source.id, "header": source.description, "length_bp": len(original), "sha256": hashlib.sha256(original.encode("ascii")).hexdigest(), "file_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()},
        "fragments": fragments,
        "reconstruction_order": list(PARTS),
        "exact_reconstruction": True,
        "identity_verification": "not_performed; source header and filename identify different accession strings",
        "assembly_design": "not_provided; no overlaps or vector sequence have been added; backbone is the trailing source remainder",
    }


def get_fragments():
    return sequence_manifest()["fragments"]


def ordering_scenario():
    fragments = get_fragments()
    wells = [f"1:A{i}" for i in range(1, 7)] + ["1:B1"]
    sources = {well: {"components": {name: 0}, "dead_volume_ul": 10, "sequence": fragments[name]} for well, name in zip(wells, PARTS)}
    sources["1:B2"] = {"components": {"water": 0}, "dead_volume_ul": 10}
    return {
        "id": "order_sequence_partitions",
        "description": "Order one aliquot of each supplied sequence partition (fragment_001 through fragment_006 and backbone), water, tips and a reaction plate. Prepare the exact 20 uL target mixture and mix it. This is a liquid-handling/sequence-inventory benchmark, not a Gibson assembly task; these adjacent source partitions have no designed overlaps and backbone is not a vector.",
        "constructed": True, "api_level": "2.19",
        "labware": {"1": "opentrons_24_tuberack_nest_1.5ml_snapcap", "2": "opentrons_96_tiprack_20ul", "3": "nest_96_wellplate_200ul_flat"},
        "pipette": {"name": "p20_single_gen2", "mount": "left", "tip_slots": ["2"]},
        "sources": sources, "sequence_inventory": fragments,
        "targets": {"3:A1": {**{name: 2 for name in PARTS}, "water": 6}},
        "mix": {"repetitions": 3, "volume_ul": 10},
        "tolerance_ul": 0.01, "tip_budget": 10, "max_simulations": 5,
        "unavailable_labware_slots": ["2", "3"], "available_tips": {"2": 0},
        "ordering": {"budget_cents": 110000, "source_capacity_ul": {well: 1500 for well in sources}},
        "sequence_note": "FASTA identity is checked by sequence and file hashes. Physical stock volumes, concentrations and prices are constructed assumptions, not measurements.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = sequence_manifest()
    payload = json.dumps(manifest, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print(payload)


def read_sequence_metadata(metadata):
    """Read a specific record from a repository FASTA, checking its saved identity."""
    path = (ROOT / metadata["sequence_file"]).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Sequence path must remain inside the repository")
    with path.open() as stream:
        records = SeqIO.to_dict(SeqIO.parse(stream, "fasta"))
    record = records[metadata["record_id"]]
    sequence = str(record.seq).upper()
    if not sequence or set(sequence) - set("ACGT"):
        raise ValueError("Sequence must be nonempty, unambiguous DNA")
    if (len(sequence) != metadata["length_bp"] or
        hashlib.sha256(sequence.encode("ascii")).hexdigest() != metadata["sha256"] or
        hashlib.sha256(path.read_bytes()).hexdigest() != metadata["file_sha256"]):
        raise ValueError("Sequence identity changed since task creation")
    return sequence


def biochemistry_inventory(scenario):
    """Identify actual input records, excluding the expected product reference."""
    spec = scenario["biochemistry"]
    if spec.get("input_design_manifest"):
        from src.sequence_assembly import verify_design
        verify_design()
    path = (ROOT / spec["sequence_file"]).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Sequence path must remain inside the repository")
    with path.open() as stream:
        records = SeqIO.to_dict(SeqIO.parse(stream, "fasta"))
    inventory = {}
    for component, definition in spec["dna"].items():
        record = records[definition["sequence_id"]]
        sequence = str(record.seq).upper()
        if not sequence or set(sequence) - set("ACGT"):
            raise ValueError("Biochemistry DNA must be unambiguous A/C/G/T")
        inventory[component] = {
            "name": component, "record_id": record.id,
            "sequence_file": spec["sequence_file"], "length_bp": len(sequence),
            "sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source": "constructed_overlap_designed_biochemistry_input",
            **({"raw_input": definition["raw_input"], "core_length_bp": definition["core_length_bp"], "three_prime_overlap_bp": definition["three_prime_overlap_bp"]} if "raw_input" in definition else {}),
            "assembly_design": "declared in the biochemistry task; experimental success not measured",
        }
    return inventory


def biochemistry_catalogue_items():
    scenarios = json.loads((ROOT / "data/biochemistry_tasks.json").read_text())
    legacy = ROOT / "data/legacy_synthetic_tasks.json"
    if legacy.exists():
        scenarios += json.loads(legacy.read_text())
    items = {}
    for scenario in scenarios:
        for name, metadata in biochemistry_inventory(scenario).items():
            item_id = scenario["biochemistry"].get("catalogue_prefix", "gibson_") + name
            item = {
                "category": "reagent", "description": f"Synthetic biochemical DNA input: {name}",
                "price_cents": 15000, "unit": "50 uL aliquot", "volume_ul": 50,
                "component": name, "sequence": metadata,
                "concentration_ng_per_ul": scenario["biochemistry"]["dna"][name]["concentration_ng_ul"],
                "physical_stock_provenance": "constructed benchmark assumption from biochemistry task; not measured",
            }
            if item_id in items and items[item_id] != item:
                raise ValueError(f"Conflicting biochemistry catalogue item: {item_id}")
            items[item_id] = item
    return items


if __name__ == "__main__":
    main()
