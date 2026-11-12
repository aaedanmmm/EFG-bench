"""Exact sequence checks for a constructed linear DNA design challenge."""
import json
import re
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq

from src.biochemistry import dna_sequence, numeric
from src.design_ordering import synthesis_policy
from src.scenarios import ROOT

ECORI_SITE = "GAATTC"
ECORI_CUT_OFFSET = 1
ECORI_END = "AATT"
MIN_DIGEST_FLANK_BP = 6
BLOCKED_MOTIF = "GCTGACCCGT" * 3 + ECORI_SITE + "CGGCTCAGTC" * 3
TARGET_FILE = ROOT / "data/sequences/design_target.fasta"


def load_design_scenarios(scenario_file=None):
    """Load the demo scenario or override its target and settings from JSON."""
    target = dna_sequence(SeqIO.read(TARGET_FILE, "fasta").seq)
    if target.count(BLOCKED_MOTIF) != 1 or target.count(ECORI_SITE) != 1:
        raise ValueError("The design target must contain the blocked region and EcoRI site once each")
    scenario = {
        "id": "gene_design_assembly",
        "description": (
            "Design and order your own DNA fragments to reconstruct the supplied synthetic "
            "noncoding target exactly as a linear product in its displayed 5′ to 3′ orientation. "
            "This constructed sequence stands in for a specified gene. Choose an assembly strategy "
            "that satisfies the synthesis constraints and submit an experiment by the deadline "
            "with sufficient correct-product yield."
        ),
        "target_sequence": target,
        "assembly": {
            "min_overlap_bp": 35,
            "max_overlap_bp": 48,
            "restriction_enzymes": {
                "ecori": {
                    "recognition_site": ECORI_SITE,
                    "top_strand_cut": "G/AATTC",
                    "cohesive_end": ECORI_END,
                    "minimum_flanking_bases_per_side": MIN_DIGEST_FLANK_BP,
                    "source": "https://www.neb.com/en-us/tools-and-resources/selection-charts/alphabetized-list-of-recognition-specificities",
                    "flanking_basis": (
                        "Constructed deterministic gate based on NEB's general end-cleavage guidance"
                    ),
                    "flanking_source": "https://www.neb.com/en-us/tools-and-resources/usage-guidelines/cleavage-close-to-the-end-of-dna-fragments",
                },
            },
            "assumptions": (
                "Overlap assembly and cohesive-end ligation consumables are available. "
                "Join exact terminal overlaps on uncut ends or matching cohesive ends from digestion. "
                "Input pieces are used in their displayed orientation. Select pieces with uncut "
                "outer ends for the linear target. This is an idealized sequence model."
            ),
        },
        "synthesis": {
            "min_length_bp": 300,
            "max_length_bp": 705,
            "blocked_motifs": [BLOCKED_MOTIF],
        },
        "budget_cents": 35000,
        "experiments": {
            "target_length_bp": len(target),
            "initial_yield_ng": 100,
            "yield_half_life_minutes": 40,
            "background_loss_per_junction": 0.05,
        },
        "assay_price_cents": 1000,
        "minimum_correct_yield_ng": 40,
        "deadline_minutes": 150,
    }
    if scenario_file is not None:
        scenario = _apply_scenario_overrides(scenario, json.loads(Path(scenario_file).read_text()))
    return [scenario]


def _apply_scenario_overrides(scenario, overrides):
    if not isinstance(overrides, dict):
        raise ValueError("Scenario overrides must be a JSON object")
    if set(overrides) - set(scenario):
        raise ValueError("Scenario JSON contains unknown fields")
    if not isinstance(overrides.get("target_sequence"), str):
        raise ValueError("Scenario JSON requires a target_sequence string")
    target = dna_sequence("".join(overrides["target_sequence"].split()))
    synthesis = overrides.get("synthesis")
    if not isinstance(synthesis, dict) or "blocked_motifs" not in synthesis:
        raise ValueError("Scenario JSON requires synthesis.blocked_motifs")

    nested_fields = {
        "synthesis": {"min_length_bp", "max_length_bp", "blocked_motifs"},
        "assembly": {"min_overlap_bp", "max_overlap_bp"},
        "experiments": {"initial_yield_ng", "yield_half_life_minutes", "background_loss_per_junction"},
    }
    merged = scenario | {
        "description": (
            "Design and order your own DNA fragments to reconstruct the supplied target "
            "exactly as a linear product in its displayed 5′ to 3′ orientation. Choose an "
            "assembly strategy that satisfies the synthesis constraints and submit an "
            "experiment by the deadline with sufficient correct-product yield."
        ),
    } | overrides | {"target_sequence": target}
    for field, allowed in nested_fields.items():
        settings = overrides.get(field, {})
        if not isinstance(settings, dict) or set(settings) - allowed:
            raise ValueError(f"Invalid scenario fields in {field}")
        merged[field] = scenario[field] | settings

    policy = synthesis_policy(merged["synthesis"])
    motifs = policy["blocked_motifs"]
    opposite = str(Seq(target).reverse_complement())
    if any(motif not in target and motif not in opposite for motif in motifs):
        raise ValueError("Each blocked motif must occur in the target in at least one orientation")
    merged["synthesis"]["blocked_motifs"] = motifs

    low = merged["assembly"]["min_overlap_bp"]
    high = merged["assembly"]["max_overlap_bp"]
    if type(low) is not int or type(high) is not int or not 1 <= low <= high:
        raise ValueError("Overlap bounds must be positive ordered integers")
    if not isinstance(merged["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", merged["id"]):
        raise ValueError("id must contain only ASCII letters, digits, underscores or hyphens")
    if not isinstance(merged["description"], str) or not merged["description"].strip():
        raise ValueError("description must be nonempty text")
    for field in ("budget_cents", "assay_price_cents", "deadline_minutes"):
        if type(merged[field]) is not int or merged[field] <= 0:
            raise ValueError(f"{field} must be a positive integer")
    numeric(merged["minimum_correct_yield_ng"], positive=True)
    experiments = merged["experiments"]
    experiments["target_length_bp"] = len(target)
    numeric(experiments["initial_yield_ng"], positive=True)
    numeric(experiments["yield_half_life_minutes"], positive=True)
    if numeric(experiments["background_loss_per_junction"]) > 1:
        raise ValueError("background_loss_per_junction cannot exceed 1")
    return merged


def digest(sequence, enzyme):
    """Return ordered 5′ to 3′ pieces and mark the new cohesive ends."""
    if enzyme != "ecori":
        raise ValueError(f"Unsupported restriction enzyme: {enzyme}")
    sequence = dna_sequence(sequence)
    sites = [
        site.start()
        for site in re.finditer(ECORI_SITE, sequence)
        if site.start() >= MIN_DIGEST_FLANK_BP
        and len(sequence) - site.end() >= MIN_DIGEST_FLANK_BP
    ]
    if not sites:
        raise ValueError("No EcoRI site with at least six flanking bases on each side")
    boundaries = [0, *(site + ECORI_CUT_OFFSET for site in sites), len(sequence)]
    return [
        {
            "sequence": sequence[left:right],
            "left_end": ECORI_END if left else None,
            "right_end": ECORI_END if right < len(sequence) else None,
        }
        for left, right in zip(boundaries, boundaries[1:])
    ]


def assemble(fragments, config):
    """Join ordered sequence records with unique homology or compatible cut ends."""
    if not fragments:
        raise ValueError("Provide at least one DNA piece")
    pieces = [
        {"sequence": dna_sequence(piece), "left_end": None, "right_end": None}
        if isinstance(piece, str)
        else {**piece, "sequence": dna_sequence(piece["sequence"])}
        for piece in fragments
    ]
    if pieces[0]["left_end"] is not None or pieces[-1]["right_end"] is not None:
        raise ValueError("A linear product needs uncut outer ends")

    product = pieces[0]["sequence"]
    for junction, (left, right) in enumerate(zip(pieces, pieces[1:]), start=1):
        left_end, right_end = left["right_end"], right["left_end"]
        if left_end is not None or right_end is not None:
            if left_end != ECORI_END or right_end != ECORI_END:
                raise ValueError(f"Junction {junction} has incompatible cohesive ends")
            product += right["sequence"]
            continue

        first, second = left["sequence"], right["sequence"]
        upper = min(config["max_overlap_bp"], len(first) - 1, len(second) - 1)
        overlaps = [
            length
            for length in range(config["min_overlap_bp"], upper + 1)
            if first[-length:] == second[:length]
        ]
        if len(overlaps) != 1:
            raise ValueError(f"Junction {junction} requires one exact terminal overlap, found {len(overlaps)}")
        product += second[overlaps[0]:]
    return product
