"""Deterministic simulated pricing for the gene-design benchmark."""

import copy
import json
from pathlib import Path

from Bio.Align import PairwiseAligner

MAX_ORDER_LENGTH_BP = 1000

_SNAPSHOT = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "design_ordering_catalogue.json").read_text()
)
_TIERS = _SNAPSHOT["synthesis"]["price_tiers"]
_COMPLEMENT = str.maketrans("ACGT", "TGCA")


def catalogue():
    """Return enzyme packs indexed by the IDs accepted for ordering."""
    return copy.deepcopy(_SNAPSHOT["items"])


def _normalize_sequence(sequence):
    if not isinstance(sequence, str):
        raise ValueError("DNA sequence must be text")
    sequence = "".join(sequence.split()).upper()
    if not sequence or set(sequence) - set("ACGT"):
        raise ValueError("DNA sequence must contain only A, C, G and T")
    return sequence


def synthesis_policy(synthesis):
    """Expose the public tariff and scenario-specific manufacturability rules."""
    vendor_minimum = _TIERS[0]["min_length_bp"]
    vendor_maximum = min(MAX_ORDER_LENGTH_BP, _TIERS[-1]["max_length_bp"])
    minimum = synthesis.get("min_length_bp", vendor_minimum)
    maximum = synthesis.get("max_length_bp", vendor_maximum)
    if (
        type(minimum) is not int
        or type(maximum) is not int
        or not vendor_minimum <= minimum <= maximum <= vendor_maximum
    ):
        raise ValueError(f"Synthesis length limits must fit within {vendor_minimum}–{vendor_maximum} bp")
    motifs = synthesis.get("blocked_motifs", [])
    if not isinstance(motifs, list):
        raise ValueError("blocked_motifs must be a list of DNA sequences")
    exons = synthesis.get("blocked_exons", [])
    if not isinstance(exons, list):
        raise ValueError("blocked_exons must be a list of DNA sequences")
    threshold = synthesis.get("exon_similarity_threshold", 0.8)
    if type(threshold) not in (int, float) or not 0 < threshold <= 1:
        raise ValueError("exon_similarity_threshold must be greater than zero and at most one")
    return {
        **copy.deepcopy(_SNAPSHOT["synthesis"]),
        "currency": _SNAPSHOT["currency"],
        "price_snapshot_date": _SNAPSHOT["price_snapshot_date"],
        "pricing_note": _SNAPSHOT["pricing_note"],
        "min_length_bp": minimum,
        "max_length_bp": maximum,
        "blocked_motifs": [_normalize_sequence(motif) for motif in motifs],
        "blocked_exons": [_normalize_sequence(exon) for exon in exons],
        "exon_similarity_threshold": threshold,
        "manufacturability_rule": (
            "Reject complete blocked motifs or exon similarity >= exon_similarity_threshold, "
            "in either orientation. Similarity = 1 - minimum edit distance between the entire "
            "exon and any fragment substring / exon length. Substitutions, insertions and "
            "deletions each cost one; unrelated fragment flanks are free."
        ),
    }


def exon_similarity(sequence, exon):
    """Full-exon normalized edit similarity to the best substring on either strand."""
    sequence, exon = _normalize_sequence(sequence), _normalize_sequence(exon)
    aligner = PairwiseAligner(mode="global", match_score=0, mismatch_score=-1,
                              open_gap_score=-1, extend_gap_score=-1)
    # Extra fragment bases at either end do not dilute an internal exon hit.
    if hasattr(aligner, "left_insertion_score"):
        aligner.left_insertion_score = 0
        aligner.right_insertion_score = 0
    else:  # Biopython 1.85 names.
        aligner.target_left_gap_score = 0
        aligner.target_right_gap_score = 0
    distance = -max(aligner.score(exon, sequence),
                    aligner.score(exon, sequence.translate(_COMPLEMENT)[::-1]))
    return max(0.0, 1 - distance / len(exon))


def quote_fragment(sequence, synthesis):
    """Quote one tube of linear double-stranded DNA if it can be synthesized."""
    sequence = _normalize_sequence(sequence)
    length = len(sequence)
    policy = synthesis_policy(synthesis)
    minimum, maximum = policy["min_length_bp"], policy["max_length_bp"]
    if not minimum <= length <= maximum:
        raise ValueError(f"Synthesis requires fragments of {minimum}–{maximum} bp. Requested {length} bp.")
    reverse_complement = sequence.translate(_COMPLEMENT)[::-1]
    if any(motif in sequence or motif in reverse_complement for motif in policy["blocked_motifs"]):
        raise ValueError("Fragment contains a complete blocked synthesis motif")
    for number, exon in enumerate(policy["blocked_exons"], 1):
        similarity = exon_similarity(sequence, exon)
        if similarity + 1e-12 >= policy["exon_similarity_threshold"]:
            raise ValueError(
                f"Fragment exceeds exon similarity limit: exon {number} ({len(exon)} bp), "
                f"similarity {similarity:.4f} >= {policy['exon_similarity_threshold']:.4f}"
            )
    tier = next(tier for tier in _TIERS if length <= tier["max_length_bp"])
    price = tier["flat_price_cents"] if "flat_price_cents" in tier else length * tier["price_cents_per_bp"]
    return {
        "sequence": sequence,
        "length_bp": length,
        "price_cents": price,
        "currency": _SNAPSHOT["currency"],
    }
