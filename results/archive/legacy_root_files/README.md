# Former loose historical results

These thirteen files previously sat directly under `results/`. Their outcomes
describe earlier repository states. See the [current results](../../README.md)
for the submission's active evidence. Saved reports retain their original bytes,
commands, paths, and source hashes; the two helper scripts have updated paths.

| Files | Purpose |
| --- | --- |
| `tests.txt`, `tests.xml`, `validation.json` | Initial test results and reproducibility metadata |
| `biochemistry_tests.txt`, `biochemistry_tests.xml`, `biochemistry_reference.json` | Earlier biochemical checks and constructed reference |
| `reference_validation.json` | Initial constructed mixing reference validation |
| `native_reference_validation.json`, `native_reference_validation_opentrons10.json` | SDK compatibility checks for the earlier references |
| `kimi_revalidation.json` | Replay of the initial actual mixing submissions |
| `rename_abc-2_validation.txt` | Earlier task-entry-point rename check |
| `revalidate.py` | Bounded-runtime replay helper for saved model artifacts |
| `check_native.py` | Native SDK helper for trusted reference protocols |

The original raw partition report is part of current provenance rather than this
archive: [raw_partition_baseline.json](../../supplied_sequence_assembly/raw_partition_baseline.json).
It was moved without changing its contents.

Equivalent local replay command from the repository root (no model API call):

```sh
.venv/bin/python results/archive/legacy_root_files/revalidate.py \
  results/archive/rollouts/20261021T065832Z \
  --output results/local_checks/mixing_replay.json
```

Create the output directory before running the helper. Historical JSON reports
still record their original locations; the [loose-file manifest](../loose_file_relocation_manifest.json)
maps them to the archive paths.
