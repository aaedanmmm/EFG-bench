# Assembly from data/sequences

Active `biochemistry`, `biochemistry_ordering`, and `failures` suites use all
seven pieces in `data/sequences`: fragments 001 through 006 and the trailing
remainder named backbone. The complete target is the original **12,484 bp**
sequence. The input FASTA files have not been changed.

| Component | Source well | Raw core length | Prepared stock / intact gel band |
| --- | --- | ---: | ---: |
| fragment_001 | 1:A1 | 742 bp | 772 bp |
| fragment_002 | 1:A2 | 1536 bp | 1566 bp |
| fragment_003 | 1:A3 | 1105 bp | 1135 bp |
| fragment_004 | 1:A4 | 618 bp | 648 bp |
| fragment_005 | 1:A5 | 1893 bp | 1923 bp |
| fragment_006 | 1:A6 | 1270 bp | 1300 bp |
| backbone | 1:B1 | 5320 bp | 5350 bp |

The original file is named `ENST00000297261.7.fasta` but its record header is
`ENSG00000164690.8 genomic`. External accession/identity verification is not
claimed; the local input's bases and hashes define the benchmark target.

## Explicit overlap preparation

The raw pieces are adjacent partitions with no terminal homology of 20-40 bases.
They cannot satisfy the existing Gibson checker unchanged. A separate generated
file, `data/biochemistry/supplied_partitions_gibson.fasta`, contains prepared
copies: each exact raw core followed by the next core's first **30 bases**.
Backbone receives the first 30 bases of fragment_001 to close the circular target.
No original base is edited or removed. Collapsing the seven shared overlaps
reconstructs the original sequence exactly, including its original start position.

`supplied_partition_design.json` records raw paths, file/base hashes, coordinates,
core lengths, prepared lengths/hashes and overlap sources. The loader verifies
this provenance and refuses stale raw/prepared stock identities. `read_sequence`
returns prepared bases plus their raw-input metadata; the raw partitions remain
separately available in the non-biochemical sequence-ordering task. A raw aliquot
cannot substitute for an overlap-prepared stock, even if its component name is
identical.

Preparation of overlap-ready DNA is a **constructed stock assumption**, such as
DNA synthesized in advance, not a PCR or preparation step performed by the OT-2.
The named backbone remains a source remainder, not an added cloning vector.
Circularity is a benchmark target topology, not a claim of a functional plasmid.

## Task and reaction configuration

| Suite | Active sample IDs |
| --- | --- |
| biochemistry | sequence_assembly |
| biochemistry_ordering | sequence_assembly_order_supplies |
| failures | sequence_recovery_01 through sequence_recovery_05 |

The target mixture contains 1 uL of each of seven prepared DNA stocks, 10 uL
of 2X enzyme-containing master mix at 1:B2, and 3 uL water at 1:B3. Constructed
stock concentrations make each 1 uL DNA input 0.03 pmol; total DNA is 0.21 pmol
and all six insert/backbone ratios are 1:1. Mix after final addition and incubate
at 50 C for 60 minutes. The reference protocol is
`examples/supplied_sequence_assembly.py`; each target is in module well 4:A1.
The checker evaluates 37 acceptance gates, including full sequence identity.

These seven-piece stock amounts, ratios and incubation bounds are **benchmark
acceptance gates**, extrapolating beyond the cited [NEB 4-6-piece formulation](https://www.neb.com/en/protocols/gibson-assembly-master-mix-assembly).
They are not a validated seven-piece wet-lab protocol or a prediction of yield.
The same distinction appears in each affected score gate's basis.

Preloaded assembly/recovery tasks have a $700 shared ordering/service budget,
allowing diagnosis of seven input stocks. The missing-supplies task has a $1300
budget; one full set of stocks and labware costs $1266.50 at the existing
constructed catalogue prices. Consumables, service fees and reagent prices have
not been changed. The per-run tip budget is 12; the reference uses nine.

## Failure diagnostics and repair

- Inactive ligase: enzyme-containing mix at 1:B2; replace `gibson_master_mix`.
- Damaged DNA: fragment_003 at 1:A3; replace `sequence_fragment_003`.
- Absent DNA: fragment_005 at 1:A5; replace `sequence_fragment_005`.
- High/low block: offset +12/-12 C; paid thermometer check then calibration.

All faults are hidden from public task metadata. The diagnostic reference maps
all seven source wells to their prepared intact band sizes, while retaining raw
core/added-overlap lengths. Source gels localize DNA faults; reaction gels alone
need not uniquely identify the defective piece. The expected product band is
12,484 bp. A healthy block reads 50 C at a 50 C setpoint; faulty blocks read
62/38 C. Correct fixes persist; pre-repair reaction samples remain failed.

The old three-piece profiles live in `data/legacy_synthetic_tasks.json` and are
only retrievable by their old IDs for historical results/regression tests. They
are not included in any active assembly or failure dataset. Their catalogue IDs
use `gibson_`; current prepared DNA uses `sequence_`, avoiding identity collisions.

## Reproduce

```sh
# Verify current inputs and prepared copies without changing anything.
.venv/bin/python -m src.sequence_assembly --check
# Regenerate derived inputs/configuration; raw FASTA inputs remain untouched.
.venv/bin/python -m src.sequence_assembly
.venv/bin/python -m src.validate examples/supplied_sequence_assembly.py \
  --scenario sequence_assembly --output results/supplied_sequence_assembly/reference.json
.venv/bin/python -m src.validate_failures \
  --output results/supplied_sequence_assembly/failure_controls.json
.venv/bin/python -m src.validate_diagnostics \
  --output results/supplied_sequence_assembly/diagnostics.json
.venv/bin/python -m pytest -q tests \
  --junitxml=results/supplied_sequence_assembly/tests.xml
```

A model run uses the same suites as before, for example
`python -m src.run_eval --suite failures --limit 1`. That run exposes the
sequence-derived task metadata to the selected provider and allows sequence access
through `read_sequence`. After explicit user approval of that data transfer, one real OpenRouter/Kimi K3
ligase-recovery rollout passed with these seven inputs. Its complete log, generated
protocol, experiment history and successful independent replay are saved under
`results/supplied_sequence_assembly/`. This run does not establish model recovery
for the other four faults. The initial pre-approval attempt was rejected before
execution; earlier logs are retained and belong to earlier benchmark inputs.
