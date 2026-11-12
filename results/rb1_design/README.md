# RB1 reference and offline validation

The gene-design default now uses human RB1 spliced cDNA ENST00000267163.6
(GRCh38), including UTRs. Reference retrieved on 2026-11-12 using Python's
`urllib.request.urlopen` against these public Ensembl URLs:

- https://rest.ensembl.org/lookup/id/ENST00000267163?expand=1;content-type=application/json
- https://rest.ensembl.org/sequence/id/ENST00000267163?type=cdna;content-type=application/json

Raw responses are `ensembl_transcript.json` and `ensembl_cdna.json`. The
27 exon sequences were sliced from the returned cDNA using cumulative exon
lengths (`genomic_end - genomic_start + 1`) in transcript order. Their lengths
sum to 4,768 bp and their concatenation equals the returned cDNA exactly.
`exon_lengths.tsv` records lengths and 1-based inclusive transcript coordinates.
The reference range is 31–1,893 bp, including UTR sequence in terminal exons.
SHA-256 checksums are recorded in `validation.json`.

## Configuration and outcome

Maximum order length: 1,000 bp, including flanks; minimum: 300 bp.
Reject normalized exon edit similarity >= 0.80 on either strand. Align the
entire exon to the best substring of the fragment, with unit substitution,
insertion, and deletion costs and free fragment flanks. Similarity is
`max(0, 1 - minimum_edit_distance / exon_length)`.
Both quoting and actual purchasing invoke the same screen. An override cannot
increase the cap beyond 1,000 bp. Custom targets do not inherit RB1 exon
sequences; they must explicitly supply `blocked_exons` when desired.

These are deterministic offline controls, **not an agent rollout or model
judge**. No model was called for this change (model: none). Historical actual
agent rollouts remain under `results/gene_design/` with their original target.
A new rollout, if undertaken, must use an `openrouter/` model.

Run from the repository root with the existing Python 3.12 environment:

```sh
python -m pytest tests/test_rb1_design.py tests/test_design_ordering.py tests/test_design_assembly.py tests/test_design_lab.py tests/test_design_experiments.py -q
python -m pytest -q
python -m src.validate examples/gibson_assembly.py --scenario gibson_assembly
```

- `focused_tests.txt`: **40 passed**, covering reference consistency, the size
  boundary, reverse complements, mutated/internal exon hits, exact threshold
  boundaries, insertion handling, partial matches, full-exon normalization,
  invalid configuration, atomic purchase rejection, and the prior synthetic
  assembly/yield controls. Synthetic controls now load an explicitly retained
  constructed fixture (`tests/fixtures/synthetic_design.json`).
- `validation.json`: actual offline quote checks reject the full target at
  4,768 bp and reject 300/1,000 bp target-prefix orders for complete exon 1.
- `full_tests.txt`: **164 passed, 67 failed, 22 errors**. The broader simulation
  checks could not complete successfully in this environment.
  `simulator_diagnostic.txt` isolates the missing `opentrons` import. No broad
  suite success is claimed.

## Feasibility limitation

The requested screen and existing assembly gates do not provide a solvable
RB1 benchmark. Exon 24 is 31 bp, shorter than the 35 bp minimum overlap. An
exact overlap assembly must put the entire exon into at least one stock,
even if a junction splits it. EcoRI does not cut within this exon. Thus
rejecting all highly similar exon-containing stocks prevents this route.
The retained $350 budget is also below the target's minimum base synthesis
cost plus the cheapest polymerase and one assay ($333.76 + $75 + $10).
The restriction has not been weakened or portrayed as a validated solvable
challenge. No successful RB1 rollout is claimed.
