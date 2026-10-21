# Historical results archive

These folders describe earlier benchmark versions, intermediate validation, and
the repository review. They are retained for provenance, including unsuccessful
model attempts. Their statements about "current" or "final" status apply to the
repository state when those artifacts were recorded. Start with the
[current results index](../README.md) for the submission's active evidence.

| Folder | Historical evidence |
| --- | --- |
| [biochemistry](biochemistry/README.md) | Earlier three-piece assembly validation and controls |
| [biochemistry_ordering](biochemistry_ordering/README.md) | Earlier order-to-reaction integration |
| [biochemistry_refactor](biochemistry_refactor/README.md) | Checker refactor and before/after comparison |
| [biochemistry_reference_review](biochemistry_reference_review/report.md) | Constructed three-piece reference review |
| [diagnostic_observability](diagnostic_observability/README.md) | Earlier diagnostic observability controls |
| [failure_system_review](failure_system_review/README.md) | Legacy failed-lot removal and historical replay assessment |
| [failures](failures/README.md) | Earlier recovery controls and real model attempts |
| [ordering](ordering/README.md) | Earlier ordering runs, including the retired failed-lot task |
| [repo_review_20261021](repo_review_20261021/README.md) | Repository review and pre-fix feedback leak reproduction |
| [rollouts](rollouts/) | Initial mixing and three-piece assembly model runs |
| [sequences](sequences/README.md) | Raw sequence partition and ordering validation |

The [earlier results index](legacy_results_index.md) preserves the detailed
historical narrative. Supporting files directly under `results/` remain in place;
the active provenance script still reads `results/sequence_partition_validation.json`.

All saved logs, JSON/XML/text evidence, generated protocols/reports, and source
snapshots were moved without changing their bytes. Navigation READMEs and seven
standalone helper scripts were updated for the extra directory level. Do not
interpret a helper's current code as the original run source; recorded hashes and
saved snapshots identify that source. Historical JSON paths and recorded commands
remain as originally recorded. Use the old-to-new paths and hashes in the
[relocation manifest](relocation_manifest.json) to locate those files.

`layout_validation.json` and `layout_replay.json` record local checks of this
archive reorganization. They are administrative validation, not new model runs.
