"""Partition the supplied sequence into six adjacent fragments and a remainder.

Run from the repository root: python3 src/split_sequence.py
This is sequence partitioning, not a cloning or assembly design.
"""

import hashlib
import json
from pathlib import Path
import platform
import shlex
import sys


def read_fasta(path):
    lines = path.read_text().splitlines()
    if not lines or not lines[0].startswith(">"):
        raise ValueError(f"Missing FASTA header: {path}")
    if any(line.startswith(">") for line in lines[1:]):
        raise ValueError(f"Expected a single FASTA record: {path}")
    sequence = "".join("".join(lines[1:]).split())
    if not sequence or set(sequence) - set("ACGT"):
        raise ValueError(f"Expected nonempty uppercase A/C/G/T sequence: {path}")
    return lines[0][1:], sequence


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    directory = Path("data/sequences")
    source = directory / "ENST00000297261.7.fasta"
    header, sequence = read_fasta(source)
    # Fixed, deliberately varied lengths within 500-2000 bp so reruns are reproducible.
    fragment_lengths = [742, 1536, 1105, 618, 1893, 1270]
    fragment_count = len(fragment_lengths)
    if not all(500 <= length <= 2000 for length in fragment_lengths):
        raise ValueError("Fragment lengths must be within 500-2000 bp")
    if len(sequence) <= sum(fragment_lengths):
        raise ValueError("Input must leave a nonempty backbone remainder")

    pieces = []
    start = 0
    for index in range(fragment_count + 1):
        name = f"fragment_{index + 1:03d}" if index < fragment_count else "backbone"
        end = start + fragment_lengths[index] if index < fragment_count else len(sequence)
        subsequence = sequence[start:end]
        path = directory / f"{name}.fasta"
        description = (
            f">{name} source_file={source.name} source_header={header!r} "
            f"coordinates_1based_inclusive={start + 1}-{end} length_bp={len(subsequence)}"
        )
        path.write_text(description + "\n" + "\n".join(
            subsequence[i:i + 60] for i in range(0, len(subsequence), 60)
        ) + "\n")
        pieces.append({"file": str(path), "start_1based": start + 1,
                       "end_1based_inclusive": end, "length_bp": len(subsequence),
                       "sha256": sha256(path)})
        start = end

    # Re-read the saved files to validate the actual outputs.
    saved = [read_fasta(Path(piece["file"]))[1] for piece in pieces]
    checks = {
        "exact_source_reconstruction": "".join(saved) == sequence,
        "all_six_fragments_in_500_to_2000_bp": all(500 <= len(s) <= 2000 for s in saved[:6]),
        "fragment_lengths_match_configuration": [len(s) for s in saved[:6]] == fragment_lengths,
        "each_piece_matches_source_coordinates": all(
            s == sequence[p["start_1based"] - 1:p["end_1based_inclusive"]]
            for s, p in zip(saved, pieces)
        ),
        "adjacent_without_gaps_or_overlaps": all(
            a["end_1based_inclusive"] + 1 == b["start_1based"]
            for a, b in zip(pieces, pieces[1:])
        ),
    }
    report = {
        "type": "actual local sequence partition and validation; not an Inspect agent rollout",
        "command": shlex.join([sys.executable, *sys.argv]),
        "working_directory": str(Path.cwd()), "python": platform.python_version(),
        "model": None, "script_sha256": sha256(Path(__file__)),
        "source": str(source), "source_header": header,
        "source_sha256": sha256(source), "source_length_bp": len(sequence),
        "configuration": {"fragment_count": fragment_count, "fragment_lengths_bp": fragment_lengths,
                          "overlap_bp": 0, "backbone": "trailing source remainder; no vector added"},
        "reconstruction_order": [Path(p["file"]).stem for p in pieces],
        "pieces": pieces, "checks": checks,
        "outcome": "passed" if all(checks.values()) else "failed",
    }
    report_path = Path("results/sequence_partition_validation.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"outcome": report["outcome"], "pieces": pieces, "checks": checks}, indent=2))
    if not all(checks.values()):
        raise RuntimeError("Sequence partition validation failed")


if __name__ == "__main__":
    main()
