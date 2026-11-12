"""Deterministic simulated pricing for the gene-design benchmark."""

import copy
import json
from pathlib import Path


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
    vendor_maximum = _TIERS[-1]["max_length_bp"]
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
    return {
        **copy.deepcopy(_SNAPSHOT["synthesis"]),
        "currency": _SNAPSHOT["currency"],
        "price_snapshot_date": _SNAPSHOT["price_snapshot_date"],
        "pricing_note": _SNAPSHOT["pricing_note"],
        "min_length_bp": minimum,
        "max_length_bp": maximum,
        "blocked_motifs": [_normalize_sequence(motif) for motif in motifs],
        "manufacturability_rule": "A fragment containing a complete blocked motif in either orientation is rejected.",
    }


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
    tier = next(tier for tier in _TIERS if length <= tier["max_length_bp"])
    price = tier["flat_price_cents"] if "flat_price_cents" in tier else length * tier["price_cents_per_bp"]
    return {
        "sequence": sequence,
        "length_bp": length,
        "price_cents": price,
        "currency": _SNAPSHOT["currency"],
    }
