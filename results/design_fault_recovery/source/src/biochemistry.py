"""Gibson acceptance checks, separated into configuration, assembly and reaction.

All bounds live in the trusted task specification. This is an acceptance model,
not a kinetic simulator: passing does not demonstrate experimental success.
Each check records its observation, criterion and scientific or benchmark basis.
"""

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq

from src.scenarios import ROOT

MODEL_VERSION = "gibson_v1"
CONTENTS_TOLERANCE_UL = 1e-7
MOLAR_RATIO_TOLERANCE = 1e-8


@dataclass(frozen=True)
class AssemblyInputs:
    """Validated DNA identities and sequences, oriented for the declared assembly."""

    sequence_path: Path
    expected_product: str
    order: list[str]
    definitions: dict
    oriented_sequences: dict[str, str]


def numeric(value, *, positive=False):
    """Validate a nonnegative number, rejecting booleans and non-finite values."""
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        requirement = "positive" if positive else "nonnegative"
        raise ValueError(f"Expected a finite {requirement} number")
    return float(value)


def dna_sequence(value):
    sequence = str(value).upper()
    if not sequence or set(sequence) - set("ACGT"):
        raise ValueError("Sequences must be nonempty, unambiguous A/C/G/T DNA")
    return sequence


def circular_equal(left, right):
    """Compare circular molecules, allowing rotation and reverse complement."""
    return len(left) == len(right) and (
        left in right + right
        or str(Seq(left).reverse_complement()) in right + right
    )


def same_contents(left, right):
    """Allow only the liquid ledger's serialization tolerance in component volumes."""
    return all(
        abs(numeric(left.get(component, 0)) - numeric(right.get(component, 0)))
        <= CONTENTS_TOLERANCE_UL
        for component in set(left) | set(right)
    )


def overlap(left, right, low, high):
    """Find the longest exact suffix/prefix homology within the allowed bounds."""
    for length_bp in range(min(high, len(left), len(right)), low - 1, -1):
        if left[-length_bp:] == right[:length_bp]:
            return length_bp
    return 0


def add_check(report, identifier, passed, *, observed, expected, basis="benchmark assumption"):
    """Keep the evidence schema identical for every acceptance gate."""
    report["checks"].append({
        "id": identifier,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
        "basis": basis,
    })


def new_report(applicable):
    return {
        "applicable": applicable,
        "model": MODEL_VERSION,
        "passed": None,
        "status": "not_evaluated" if applicable else "not_applicable",
        "experimental_status": "not_measured",
        "interpretation": (
            "Passing means the declared in-silico acceptance criteria hold. "
            "No yield, colonies, enzyme activity or biological function has been measured."
        ),
        "checks": [],
        "reactions": [],
    }


def validate_criteria(spec):
    """Validate the supported profile and numerical bounds before reading evidence."""
    if spec["model"] != MODEL_VERSION or spec["topology"] != "circular":
        raise ValueError("Only gibson_v1 circular dsDNA assemblies are supported")

    criteria = spec["criteria"]
    bounded_criteria = (
        "master_mix_final_x",
        "total_dna_pmol",
        "insert_backbone_ratio",
        "vector_mass_ng",
        "overlap_bp",
        "temperature_c",
        "incubation_seconds",
    )
    for name in bounded_criteria:
        bounds = criteria[name]
        if len(bounds) != 2 or numeric(bounds[0]) > numeric(bounds[1]):
            raise ValueError(f"Invalid criteria bounds for {name}")

    numeric(criteria["dsdna_g_mol_per_bp"], positive=True)
    numeric(criteria["volume_tolerance_ul"])
    numeric(criteria["reaction_volume_ul"], positive=True)


def load_assembly_inputs(scenario, spec):
    """Read trusted FASTA records and match each declared DNA input to a sequence."""
    sequence_path = (ROOT / spec["sequence_file"]).resolve()
    if not sequence_path.is_relative_to(ROOT):
        raise ValueError("Sequence input must be inside the repository")

    records = list(SeqIO.parse(sequence_path, "fasta"))
    if len({record.id for record in records}) != len(records):
        raise ValueError("Duplicate FASTA identifiers")
    sequences = {record.id: dna_sequence(record.seq) for record in records}
    expected_product = sequences[spec["expected_product_id"]]

    order = spec["assembly_order"]
    definitions = spec["dna"]
    if (
        len(order) < 2
        or len(set(order)) != len(order)
        or set(order) != set(definitions)
        or spec["backbone"] not in order
    ):
        raise ValueError(
            "Assembly order must contain each DNA component exactly once, including the backbone"
        )
    if not spec["reaction_wells"] or not set(spec["reaction_wells"]).issubset(scenario["targets"]):
        raise ValueError("Reaction wells must be configured targets")

    oriented_sequences = {}
    for name, definition in definitions.items():
        if definition["orientation"] not in ("+", "-"):
            raise ValueError("DNA orientations must be + or -")
        numeric(definition["concentration_ng_ul"], positive=True)
        sequence = sequences[definition["sequence_id"]]
        oriented_sequences[name] = (
            sequence if definition["orientation"] == "+"
            else str(Seq(sequence).reverse_complement())
        )

    return AssemblyInputs(
        sequence_path=sequence_path,
        expected_product=expected_product,
        order=order,
        definitions=definitions,
        oriented_sequences=oriented_sequences,
    )


def check_input_metadata(report, definitions):
    supplied_metadata = {
        name: {field: definition.get(field) for field in ("linear", "purified")}
        for name, definition in definitions.items()
    }
    add_check(
        report,
        "input.linear_purified_dsdna",
        all(
            definition.get("linear") is True and definition.get("purified") is True
            for definition in definitions.values()
        ),
        observed=supplied_metadata,
        expected="All specified DNA inputs are purified linear dsDNA",
        basis="supplied metadata; not a purity assay",
    )


def terminal_partners(left_sequence, assembly, min_overlap_bp, max_overlap_bp):
    """Include self-joining and both orientations when looking for competitors."""
    candidates = []
    for name in assembly.order:
        forward = assembly.oriented_sequences[name]
        reverse = str(Seq(forward).reverse_complement())
        for direction, sequence in (("+", forward), ("-", reverse)):
            if overlap(left_sequence, sequence, min_overlap_bp, max_overlap_bp):
                candidates.append(name + direction)
    return candidates


def check_junctions(report, assembly, overlap_bounds_bp):
    min_overlap_bp, max_overlap_bp = overlap_bounds_bp
    if (
        type(min_overlap_bp) is not int
        or type(max_overlap_bp) is not int
        or min_overlap_bp < 1
        or max_overlap_bp > 200
    ):
        raise ValueError("Overlap bounds must be positive integers <=200")

    junctions = []
    for index, left_name in enumerate(assembly.order):
        right_name = assembly.order[(index + 1) % len(assembly.order)]
        left_sequence = assembly.oriented_sequences[left_name]
        right_sequence = assembly.oriented_sequences[right_name]
        overlap_bp = overlap(left_sequence, right_sequence, min_overlap_bp, max_overlap_bp)
        junctions.append({
            "left": left_name,
            "right": right_name,
            "overlap_bp": overlap_bp,
            "overlap_sequence": left_sequence[-overlap_bp:] if overlap_bp else "",
        })
        add_check(
            report,
            f"junction.{left_name}->{right_name}.homology",
            overlap_bp > 0,
            observed=overlap_bp,
            expected=f"Exact terminal overlap of {min_overlap_bp}..{max_overlap_bp} bp",
        )
        candidates = terminal_partners(left_sequence, assembly, min_overlap_bp, max_overlap_bp)
        add_check(
            report,
            f"junction.{left_name}.specificity",
            candidates == [right_name + "+"],
            observed=candidates,
            expected=[right_name + "+"],
            basis=(
                "conservative terminal-overlap uniqueness rule; "
                "includes self-joining and reverse orientations"
            ),
        )
    return junctions


def assemble_circular_product(assembly, junctions):
    """Collapse each shared overlap once, including the circular closing junction."""
    if not all(junction["overlap_bp"] for junction in junctions):
        return None
    product = assembly.oriented_sequences[assembly.order[0]]
    for index, name in enumerate(assembly.order[1:]):
        product += assembly.oriented_sequences[name][junctions[index]["overlap_bp"]:]
    return product[:-junctions[-1]["overlap_bp"]]


def check_product_identity(report, assembly, junctions):
    product = assemble_circular_product(assembly, junctions)
    expected_product = assembly.expected_product
    add_check(
        report,
        "product.sequence_identity",
        product is not None and circular_equal(product, expected_product),
        observed={
            "length_bp": len(product) if product else None,
            "sha256": hashlib.sha256(product.encode()).hexdigest() if product else None,
        },
        expected={
            "length_bp": len(expected_product),
            "sha256": hashlib.sha256(expected_product.encode()).hexdigest(),
            "comparison": (
                "Full circular sequence identity allowing rotation "
                "and whole-product reverse complement"
            ),
        },
    )
    report["assembly"] = {
        "order": assembly.order,
        "topology": "circular",
        "junctions": junctions,
        "predicted_sequence": product,
        "expected_sequence": expected_product,
        "sequence_file": str(assembly.sequence_path.relative_to(ROOT)),
        "sequence_file_sha256": hashlib.sha256(assembly.sequence_path.read_bytes()).hexdigest(),
    }


def check_master_mix_metadata(report, spec, definitions):
    master_mix = spec["master_mix"]
    numeric(master_mix["stock_concentration_x"], positive=True)
    if master_mix["component"] in definitions:
        raise ValueError("Master mix cannot also be a DNA component")
    add_check(
        report,
        "enzyme.active",
        master_mix.get("active") is True,
        observed=master_mix.get("active"),
        expected=True,
        basis="supplied reagent metadata; not an enzyme activity measurement",
    )


def check_reaction_composition(report, well, contents, spec, definitions):
    criteria = spec["criteria"]
    master_mix = spec["master_mix"]
    reaction_volume_ul = sum(numeric(quantity_ul) for quantity_ul in contents.values())
    expected_volume_ul = numeric(criteria["reaction_volume_ul"], positive=True)
    volume_tolerance_ul = numeric(criteria["volume_tolerance_ul"])
    add_check(
        report,
        f"{well}.reaction_volume",
        abs(reaction_volume_ul - expected_volume_ul) <= volume_tolerance_ul,
        observed=reaction_volume_ul,
        expected={"volume_ul": expected_volume_ul, "tolerance_ul": volume_tolerance_ul},
        basis="NEB 20 uL reference formulation, parameterized in benchmark",
    )
    allowed_components = set(definitions) | {master_mix["component"], "water"}
    unexpected_components = [
        name for name, quantity_ul in contents.items()
        if quantity_ul > CONTENTS_TOLERANCE_UL and name not in allowed_components
    ]
    add_check(
        report,
        f"{well}.reagent_identity",
        not unexpected_components,
        observed=unexpected_components,
        expected=[],
        basis="closed reagent identity model; unmodeled additives fail",
    )

    stock_concentration_x = numeric(master_mix["stock_concentration_x"], positive=True)
    master_mix_volume_ul = numeric(contents.get(master_mix["component"], 0))
    final_concentration_x = (
        stock_concentration_x * master_mix_volume_ul / reaction_volume_ul
        if reaction_volume_ul else 0
    )
    min_concentration_x, max_concentration_x = criteria["master_mix_final_x"]
    add_check(
        report,
        f"{well}.master_mix_concentration",
        min_concentration_x <= final_concentration_x <= max_concentration_x,
        observed=final_concentration_x,
        expected={"range_x": criteria["master_mix_final_x"]},
        basis="NEB 2X stock diluted to 1X; tolerance is a benchmark assumption",
    )
    return reaction_volume_ul, final_concentration_x


def calculate_dna_quantities(report, well, contents, assembly, molecular_weight_per_bp):
    """Convert stock volume to DNA mass (ng), then amount (pmol).

    pmol = mass_ng * 1000 / (length_bp * molecular_weight_g_mol_per_bp).
    The factor 1000 converts nanograms per g/mol to picomoles.
    """
    quantities = {}
    for name, definition in assembly.definitions.items():
        volume_ul = numeric(contents.get(name, 0))
        mass_ng = volume_ul * definition["concentration_ng_ul"]
        length_bp = len(assembly.oriented_sequences[name])
        amount_pmol = mass_ng * 1000 / (length_bp * molecular_weight_per_bp)
        quantities[name] = {
            "volume_ul": volume_ul,
            "mass_ng": mass_ng,
            "length_bp": length_bp,
            "pmol": amount_pmol,
            "concentration_ng_ul": definition["concentration_ng_ul"],
        }
        add_check(
            report,
            f"{well}.dna_present.{name}",
            volume_ul > 0,
            observed=volume_ul,
            expected=">0 uL",
        )
    return quantities


def check_dna_amounts(report, well, quantities, spec, molecular_weight_per_bp):
    criteria = spec["criteria"]
    backbone = quantities[spec["backbone"]]
    min_vector_mass_ng, max_vector_mass_ng = criteria["vector_mass_ng"]
    add_check(
        report,
        f"{well}.vector_mass",
        min_vector_mass_ng <= backbone["mass_ng"] <= max_vector_mass_ng,
        observed=backbone["mass_ng"],
        expected={"range_ng": criteria["vector_mass_ng"]},
        basis=spec.get("criteria_basis", "NEB recommended vector mass; enforced here as an acceptance gate"),
    )

    total_dna_pmol = sum(quantity["pmol"] for quantity in quantities.values())
    min_total_pmol, max_total_pmol = criteria["total_dna_pmol"]
    add_check(
        report,
        f"{well}.total_dna",
        min_total_pmol <= total_dna_pmol <= max_total_pmol,
        observed=total_dna_pmol,
        expected={
            "range_pmol": criteria["total_dna_pmol"],
            "formula": "mass_ng * 1000 / (length_bp * molecular_weight_per_bp)",
            "molecular_weight_g_mol_bp": molecular_weight_per_bp,
        },
        basis=spec.get("criteria_basis", "NEB E2611 DNA-input guidance; dsDNA approximation"),
    )

    insert_backbone_ratios = {}
    for name, quantity in quantities.items():
        if name == spec["backbone"]:
            continue
        ratio = quantity["pmol"] / backbone["pmol"] if backbone["pmol"] else None
        insert_backbone_ratios[name] = ratio
        min_ratio, max_ratio = criteria["insert_backbone_ratio"]
        add_check(
            report,
            f"{well}.molar_ratio.{name}",
            ratio is not None
            and min_ratio - MOLAR_RATIO_TOLERANCE <= ratio <= max_ratio + MOLAR_RATIO_TOLERANCE,
            observed=ratio,
            expected={"insert_to_backbone_range": criteria["insert_backbone_ratio"]},
            basis=spec.get("criteria_basis", "NEB recommended insert excess; enforced here as an acceptance gate"),
        )
    return total_dna_pmol, insert_backbone_ratios


def check_incubation(report, well, contents, simulation, criteria, basis=None):
    """Count only exposure of the final mixed contents at the required temperature.

    A matching revision prevents an earlier heated mixture from qualifying after
    subsequent liquid changes. Component comparison also checks the saved evidence.
    """
    min_temperature_c, max_temperature_c = criteria["temperature_c"]
    incubation_history = [
        event for event in simulation.get("events", [])
        if event.get("action") == "incubate" and event.get("well") == well
    ]
    qualifying_events = [
        event for event in incubation_history
        if min_temperature_c <= numeric(event["temperature_c"]) <= max_temperature_c
        and event.get("mixed") is True
        and event.get("revision") == simulation.get("well_revisions", {}).get(well)
        and same_contents(event.get("components_ul", {}), contents)
    ]
    qualified_seconds = sum(numeric(event["seconds"]) for event in qualifying_events)
    min_seconds, max_seconds = criteria["incubation_seconds"]
    add_check(
        report,
        f"{well}.incubation",
        min_seconds <= qualified_seconds <= max_seconds,
        observed={
            "qualified_seconds": qualified_seconds,
            "all_incubation_events": incubation_history,
        },
        expected={
            "seconds": criteria["incubation_seconds"],
            "temperature_c": criteria["temperature_c"],
            "after_final_addition_and_mixing": True,
        },
        basis=basis or (
            "NEB 50 C and 15-60 min for 2-3 fragments; temperature tolerance "
            "and final-state requirement are benchmark assumptions"
        ),
    )
    return qualified_seconds


def evaluate_reaction(report, well, spec, simulation, assembly):
    """Check composition, DNA amounts and final-state incubation for one well."""
    contents = simulation.get("final_wells", {}).get(well, {})
    criteria = spec["criteria"]
    molecular_weight_per_bp = numeric(criteria["dsdna_g_mol_per_bp"], positive=True)
    reaction_volume_ul, master_mix_final_x = check_reaction_composition(
        report, well, contents, spec, assembly.definitions
    )
    quantities = calculate_dna_quantities(
        report, well, contents, assembly, molecular_weight_per_bp
    )
    total_dna_pmol, insert_backbone_ratios = check_dna_amounts(
        report, well, quantities, spec, molecular_weight_per_bp
    )
    qualified_incubation_seconds = check_incubation(
        report, well, contents, simulation, criteria, basis=spec.get("criteria_basis")
    )
    report["reactions"].append({
        "well": well,
        "volume_ul": reaction_volume_ul,
        "master_mix_final_x": master_mix_final_x,
        "dna": quantities,
        "insert_backbone_ratios": insert_backbone_ratios,
        "total_dna_pmol": total_dna_pmol,
        "qualified_incubation_seconds": qualified_incubation_seconds,
    })


def evaluate_biochemistry(scenario, simulation):
    """Evaluate a declared Gibson profile and return the existing evidence schema.

    Checks remain ordered: configuration, input metadata, junctions, product,
    enzyme metadata, each reaction, then independent liquid handling. Malformed
    configuration or evidence retains earlier checks and adds a failure gate.
    """
    spec = scenario.get("biochemistry")
    report = new_report(applicable=spec is not None)
    if spec is None:
        return report
    report["references"] = spec.get("references", [])
    report["assumptions"] = spec.get("benchmark_assumptions", [])

    try:
        validate_criteria(spec)
        assembly = load_assembly_inputs(scenario, spec)
        check_input_metadata(report, assembly.definitions)
        junctions = check_junctions(report, assembly, spec["criteria"]["overlap_bp"])
        check_product_identity(report, assembly, junctions)
        check_master_mix_metadata(report, spec, assembly.definitions)
        for well in spec["reaction_wells"]:
            evaluate_reaction(report, well, spec, simulation, assembly)
        add_check(
            report,
            "execution.liquid_handling",
            simulation.get("liquid_handling_passed") is True,
            observed=simulation.get("liquid_handling_passed"),
            expected=True,
            basis="independent virtual-robot and liquid-accounting checks",
        )
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        # Retain the public failure gate for both invalid profiles and evidence.
        add_check(
            report,
            "configuration.valid",
            False,
            observed=f"{type(exc).__name__}: {exc}",
            expected="Complete supported biochemical specification and valid simulation evidence",
        )

    report["passed"] = bool(report["checks"]) and all(
        check["passed"] for check in report["checks"]
    )
    report["status"] = (
        "in_silico_conditions_satisfied" if report["passed"]
        else "in_silico_conditions_failed"
    )
    return report
