# Input sequences

The user-supplied single-record FASTA `ENST00000297261.7.fasta` contains 12,484 bp.
Its header is `ENSG00000164690.8 genomic`; this differs from the filename, and no
external sequence identity verification has been performed.

The derived files partition that exact sequence in its original orientation,
with no gaps, overlaps, added bases, or removed bases. Coordinates are 1-based,
inclusive:

| File | Source coordinates | Length (bp) |
| --- | --- | ---: |
| fragment_001.fasta | 1–1,000 | 1,000 |
| fragment_002.fasta | 1,001–2,000 | 1,000 |
| fragment_003.fasta | 2,001–3,000 | 1,000 |
| fragment_004.fasta | 3,001–4,000 | 1,000 |
| fragment_005.fasta | 4,001–5,000 | 1,000 |
| fragment_006.fasta | 5,001–6,000 | 1,000 |
| backbone.fasta | 6,001–12,484 | 6,484 |

Here, backbone means the trailing source remainder, not an added plasmid vector.
These are computational sequence partitions; no assembly overlaps, primers, or
cloning design have been added. Concatenating fragments 001 through 006, then
backbone, exactly reconstructs the source.

Reproduce from the repository root with `python3 src/split_sequence.py` (standard
library only). Actual output hashes and validation results are recorded in
[sequence_partition_validation.json](../../results/sequence_partition_validation.json).
This local validation is not an Inspect agent rollout.
