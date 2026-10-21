# Supplied-sequence integration evidence

> Historical evidence from an earlier repository state. See the [current results](../../README.md). Original logs, reports and source snapshots are preserved. Paths in reproduction examples reflect the archive layout; original commands remain in the saved run records.

All supplied DNA bases were kept local during this validation. No sequence-task
model rollout is claimed. Physical stock properties, prices, order requests and
the reference mixing protocol used here are constructed benchmark assumptions.

- `manifest.json`: actual Biopython validation of the seven input partitions,
  including lengths, SHA-256 hashes and source coordinates. They exactly
  reconstruct the 12,484 bp source. Identity beyond the supplied file/header
  has not been verified.
- `integration.json`: actual local ordering and real Opentrons virtual-hardware
  validation using `examples/sequence_partitions.py`. All ten supply orders
  succeeded for a simulated $1,072.50, within the $1,100 budget, and the specified
  seven-part mixture passed with eight tips. This is not an agent rollout.
- `check_integration.py`: reproduces the local check. It also invokes the restored
  partitioning script and verifies that every FASTA byte is unchanged. The
  original report is retained in
  `../../supplied_sequence_assembly/raw_partition_baseline.json`; regenerated
  reports use `results/supplied_sequence_assembly/partition_validation.json`.
- `../ordering/tests.txt` and `../ordering/tests.xml`: full test results, including
  malformed/missing FASTA rejection, source-coordinate validation, catalogue and
  receipt identity, changed-identity rejection, real simulator integration and
  isolation of sequences from synthetic ordering tasks.

Commands from the worktree root:

```sh
.venv/bin/python -m src.fragments --output results/archive/sequences/manifest.json
.venv/bin/python results/archive/sequences/check_integration.py
.venv/bin/python -m pytest -q tests --junitxml=results/archive/ordering/tests.xml
```

`backbone` here means the trailing source remainder. No overlaps, vector,
primers, cloning design or biological activity claims have been added to these
inputs. The separate biochemistry task continues to use its own synthetic,
overlap-designed sequences. An external-model sequence rollout was not run
because the required data-transfer approval has not been supplied.
