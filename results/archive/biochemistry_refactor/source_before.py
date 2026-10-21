"""Reviewable Gibson acceptance model, not a kinetic simulator or assay result.

All bounds live in the task specification. Passing these necessary benchmark
conditions is explicitly distinct from demonstrating experimental success.
"""
import hashlib
import math
from Bio import SeqIO
from Bio.Seq import Seq
from src.scenarios import ROOT

MODEL_VERSION = "gibson_v1"


def numeric(value, *, positive=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError("Expected a finite nonnegative number" if not positive else "Expected a finite positive number")
    return float(value)


def dna_sequence(value):
    value = str(value).upper()
    if not value or set(value) - set("ACGT"):
        raise ValueError("Sequences must be nonempty, unambiguous A/C/G/T DNA")
    return value


def circular_equal(left, right):
    return len(left) == len(right) and (left in right + right or str(Seq(left).reverse_complement()) in right + right)


def same_contents(left, right):
    return all(abs(numeric(left.get(key, 0)) - numeric(right.get(key, 0))) <= 1e-7 for key in set(left) | set(right))


def overlap(left, right, low, high):
    for length in range(min(high, len(left), len(right)), low - 1, -1):
        if left[-length:] == right[:length]:
            return length
    return 0


def evaluate_biochemistry(scenario, simulation):
    spec = scenario.get("biochemistry")
    report = {
        "applicable": spec is not None,
        "model": MODEL_VERSION,
        "passed": None,
        "status": "not_applicable" if spec is None else "not_evaluated",
        "experimental_status": "not_measured",
        "interpretation": "Passing means the declared in-silico acceptance criteria hold. No yield, colonies, enzyme activity or biological function has been measured.",
        "checks": [], "reactions": [],
    }
    if spec is None:
        return report
    report["references"] = spec.get("references", [])
    report["assumptions"] = spec.get("benchmark_assumptions", [])

    def check(identifier, passed, observed, expected, basis="benchmark assumption"):
        report["checks"].append({"id": identifier, "passed": bool(passed), "observed": observed, "expected": expected, "basis": basis})

    try:
        if spec["model"] != MODEL_VERSION or spec["topology"] != "circular":
            raise ValueError("Only gibson_v1 circular dsDNA assemblies are supported")
        criteria = spec["criteria"]
        for key in ("master_mix_final_x", "total_dna_pmol", "insert_backbone_ratio", "vector_mass_ng", "overlap_bp", "temperature_c", "incubation_seconds"):
            bounds = criteria[key]
            if len(bounds) != 2 or numeric(bounds[0]) > numeric(bounds[1]):
                raise ValueError(f"Invalid criteria bounds for {key}")
        mass_per_bp = numeric(criteria["dsdna_g_mol_per_bp"], positive=True)
        tolerance = numeric(criteria["volume_tolerance_ul"])
        reaction_volume = numeric(criteria["reaction_volume_ul"], positive=True)
        path = (ROOT / spec["sequence_file"]).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("Sequence input must be inside the repository")
        records = list(SeqIO.parse(path, "fasta"))
        if len({record.id for record in records}) != len(records):
            raise ValueError("Duplicate FASTA identifiers")
        sequences = {record.id: dna_sequence(record.seq) for record in records}
        expected_product = sequences[spec["expected_product_id"]]
        order, definitions = spec["assembly_order"], spec["dna"]
        if len(order) < 2 or len(set(order)) != len(order) or set(order) != set(definitions) or spec["backbone"] not in order:
            raise ValueError("Assembly order must contain each DNA component exactly once, including the backbone")
        if not spec["reaction_wells"] or not set(spec["reaction_wells"]).issubset(scenario["targets"]):
            raise ValueError("Reaction wells must be configured targets")
        oriented = {}
        for name, definition in definitions.items():
            if definition["orientation"] not in ("+", "-"):
                raise ValueError("DNA orientations must be + or -")
            numeric(definition["concentration_ng_ul"], positive=True)
            sequence = sequences[definition["sequence_id"]]
            oriented[name] = sequence if definition["orientation"] == "+" else str(Seq(sequence).reverse_complement())
        check("input.linear_purified_dsdna", all(d.get("linear") is True and d.get("purified") is True for d in definitions.values()), {n: {k: d.get(k) for k in ("linear", "purified")} for n, d in definitions.items()}, "All specified DNA inputs are purified linear dsDNA", "supplied metadata; not a purity assay")
        low, high = criteria["overlap_bp"]
        if type(low) is not int or type(high) is not int or low < 1 or high > 200:
            raise ValueError("Overlap bounds must be positive integers <=200")
        junctions, overlaps = [], []
        for index, name in enumerate(order):
            following = order[(index + 1) % len(order)]
            length = overlap(oriented[name], oriented[following], low, high)
            junctions.append({"left": name, "right": following, "overlap_bp": length, "overlap_sequence": oriented[name][-length:] if length else ""})
            overlaps.append(length)
            check(f"junction.{name}->{following}.homology", length > 0, length, f"Exact terminal overlap of {low}..{high} bp")
            candidates = []
            for candidate in order:
                for direction, seq in (("+", oriented[candidate]), ("-", str(Seq(oriented[candidate]).reverse_complement()))):
                    if overlap(oriented[name], seq, low, high):
                        candidates.append(candidate + direction)
            check(f"junction.{name}.specificity", candidates == [following + "+"], candidates, [following + "+"], "conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations")
        product = None
        if all(overlaps):
            product = oriented[order[0]]
            for index, name in enumerate(order[1:]):
                product += oriented[name][overlaps[index]:]
            product = product[:-overlaps[-1]]
        check("product.sequence_identity", product is not None and circular_equal(product, expected_product), {"length_bp": len(product) if product else None, "sha256": hashlib.sha256(product.encode()).hexdigest() if product else None}, {"length_bp": len(expected_product), "sha256": hashlib.sha256(expected_product.encode()).hexdigest(), "comparison": "Full circular sequence identity allowing rotation and whole-product reverse complement"})
        report["assembly"] = {"order": order, "topology": "circular", "junctions": junctions, "predicted_sequence": product, "expected_sequence": expected_product, "sequence_file": str(path.relative_to(ROOT)), "sequence_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        mix = spec["master_mix"]
        stock_x = numeric(mix["stock_concentration_x"], positive=True)
        if mix["component"] in definitions:
            raise ValueError("Master mix cannot also be a DNA component")
        check("enzyme.active", mix.get("active") is True, mix.get("active"), True, "supplied reagent metadata; not an enzyme activity measurement")
        for well in spec["reaction_wells"]:
            contents = simulation.get("final_wells", {}).get(well, {})
            amount = sum(numeric(qty) for qty in contents.values())
            check(f"{well}.reaction_volume", abs(amount - reaction_volume) <= tolerance, amount, {"volume_ul": reaction_volume, "tolerance_ul": tolerance}, "NEB 20 uL reference formulation, parameterized in benchmark")
            unexpected = [name for name, qty in contents.items() if qty > 1e-7 and name not in set(definitions) | {mix["component"], "water"}]
            check(f"{well}.reagent_identity", not unexpected, unexpected, [], "closed reagent identity model; unmodeled additives fail")
            final_x = stock_x * numeric(contents.get(mix["component"], 0)) / amount if amount else 0
            check(f"{well}.master_mix_concentration", criteria["master_mix_final_x"][0] <= final_x <= criteria["master_mix_final_x"][1], final_x, {"range_x": criteria["master_mix_final_x"]}, "NEB 2X stock diluted to 1X; tolerance is a benchmark assumption")
            quantities = {}
            for name, definition in definitions.items():
                used = numeric(contents.get(name, 0))
                mass = used * definition["concentration_ng_ul"]
                length = len(oriented[name])
                pmol = mass * 1000 / (length * mass_per_bp)
                quantities[name] = {"volume_ul": used, "mass_ng": mass, "length_bp": length, "pmol": pmol, "concentration_ng_ul": definition["concentration_ng_ul"]}
                check(f"{well}.dna_present.{name}", used > 0, used, ">0 uL")
            backbone = quantities[spec["backbone"]]
            vector_range = criteria["vector_mass_ng"]
            check(f"{well}.vector_mass", vector_range[0] <= backbone["mass_ng"] <= vector_range[1], backbone["mass_ng"], {"range_ng": vector_range}, "NEB recommended vector mass; enforced here as an acceptance gate")
            total_pmol = sum(q["pmol"] for q in quantities.values())
            bounds = criteria["total_dna_pmol"]
            check(f"{well}.total_dna", bounds[0] <= total_pmol <= bounds[1], total_pmol, {"range_pmol": bounds, "formula": "mass_ng * 1000 / (length_bp * molecular_weight_per_bp)", "molecular_weight_g_mol_bp": mass_per_bp}, "NEB E2611 DNA-input guidance; dsDNA approximation")
            ratios = {}
            for name, quantity in quantities.items():
                if name != spec["backbone"]:
                    ratio = quantity["pmol"] / backbone["pmol"] if backbone["pmol"] else None
                    ratios[name] = ratio
                    bounds = criteria["insert_backbone_ratio"]
                    check(f"{well}.molar_ratio.{name}", ratio is not None and bounds[0] - 1e-8 <= ratio <= bounds[1] + 1e-8, ratio, {"insert_to_backbone_range": bounds}, "NEB recommended insert excess; enforced here as an acceptance gate")
            temp, times = criteria["temperature_c"], criteria["incubation_seconds"]
            history = [event for event in simulation.get("events", []) if event.get("action") == "incubate" and event.get("well") == well]
            qualifying = [event for event in history if temp[0] <= numeric(event["temperature_c"]) <= temp[1] and event.get("mixed") is True and event.get("revision") == simulation.get("well_revisions", {}).get(well) and same_contents(event.get("components_ul", {}), contents)]
            seconds = sum(numeric(event["seconds"]) for event in qualifying)
            check(f"{well}.incubation", times[0] <= seconds <= times[1], {"qualified_seconds": seconds, "all_incubation_events": history}, {"seconds": times, "temperature_c": temp, "after_final_addition_and_mixing": True}, "NEB 50 C and 15-60 min for 2-3 fragments; temperature tolerance and final-state requirement are benchmark assumptions")
            report["reactions"].append({"well": well, "volume_ul": amount, "master_mix_final_x": final_x, "dna": quantities, "insert_backbone_ratios": ratios, "total_dna_pmol": total_pmol, "qualified_incubation_seconds": seconds})
        check("execution.liquid_handling", simulation.get("liquid_handling_passed") is True, simulation.get("liquid_handling_passed"), True, "independent virtual-robot and liquid-accounting checks")
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        check("configuration.valid", False, f"{type(exc).__name__}: {exc}", "Complete supported biochemical specification and valid simulation evidence")
    report["passed"] = bool(report["checks"]) and all(item["passed"] for item in report["checks"])
    report["status"] = "in_silico_conditions_satisfied" if report["passed"] else "in_silico_conditions_failed"
    return report
