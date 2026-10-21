# Input sequences

The user-supplied single-record FASTA `ENST00000297261.7.fasta` contains 12,484 bp.
Its header is `ENSG00000164690.8 genomic`; this differs from the filename, and no
external sequence identity verification has been performed.

The derived files partition that exact sequence in its original orientation,
with no gaps, overlaps, added bases, or removed bases. Coordinates are 1-based,
inclusive:

| File | Source coordinates | Length (bp) |
| --- | --- | ---: |
| fragment_001.fasta | 1–742 | 742 |
| fragment_002.fasta | 743–2278 | 1536 |
| fragment_003.fasta | 2279–3383 | 1105 |
| fragment_004.fasta | 3384–4001 | 618 |
| fragment_005.fasta | 4002–5894 | 1893 |
| fragment_006.fasta | 5895–7164 | 1270 |
| backbone.fasta | 7165–12484 | 5320 |

Here, backbone means the trailing source remainder, not an added plasmid vector.
These are computational sequence partitions; no assembly overlaps, primers, or
cloning design have been added. Concatenating fragments 001 through 006, then
backbone, exactly reconstructs the source.

Reproduce from the repository root with `python3 src/split_sequence.py` (standard
library only). Actual output hashes and validation results are recorded in
[sequence_partition_validation.json](../../results/sequence_partition_validation.json).
This local validation is not an Inspect agent rollout.

## Evaluation integration

`src/fragments.py` validates these exact files and exposes their lengths, hashes
and coordinates to the simulated ordering catalogue. The item IDs are the FASTA
stems (`fragment_001` … `fragment_006`, `backbone`). Reagent orders carry those
identities into inventory and receipts. `order_sequence_partitions` exercises
purchasing and liquid handling only; the active assembly/recovery suites now use separate overlap-ready copies
derived from all seven raw cores, with their provenance recorded in
`data/biochemistry/supplied_partition_design.json`. Each copy adds a 30 bp
3-prime overlap; none of these raw files is edited. See the
[assembly design guide](../../docs/supplied_sequence_assembly.md).

Run `.venv/bin/python -m src.fragments` to inspect the manifest, or
`.venv/bin/python results/sequences/check_integration.py` for the fully local
order-and-simulate check. Evidence is in `results/sequences/`.
