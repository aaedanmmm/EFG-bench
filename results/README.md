# Results and evidence

Start with the current seven-piece assembly/recovery evidence below. Historical
runs and intermediate assessments are retained in [archive/](archive/README.md).
All biological outcomes here are constructed in-silico acceptance results;
experimental outcomes have not been measured.

## Current submission evidence

| Folder | Contents |
| --- | --- |
| [supplied_sequence_assembly](supplied_sequence_assembly/README.md) | Actual Kimi K3 seven-piece ligase-recovery rollout, run configuration/source snapshot, reference, five fault controls, diagnostics, replay, and post-hoc judgment |
| [feedback_privacy](feedback_privacy/README.md) | Subsequent simulator-feedback privacy fix, 189 passing tests, and replay of the saved rollout |
| [judge](judge/README.md) | Judge calibration and refusal controls, with earlier actor-trace assessments identified as historical |

The actual current-input model evidence covers **one ligase-recovery sample**.
The other four faults have constructed controls, rather than established model
recoveries. The saved actor transcript predates the feedback privacy fix; the
subsequent replay verifies scoring compatibility, not behavior under the revised
feedback. The post-hoc judgment uses the same model family as the actor and is
not an independent behavioral assessment.

The earlier **3/3 mixing result** belongs to the initial benchmark and is retained
in the [historical results index](archive/legacy_results_index.md). It does not
establish success on all five current recovery tasks.

## Archive and supporting files

[archive/README.md](archive/README.md) indexes eleven historical folders,
including unsuccessful model attempts. The [relocation manifest](archive/relocation_manifest.json)
maps their original paths to archived paths and records original/current hashes.
Historical logs and evidence retain their original contents, recorded paths,
commands, and source hashes.

Root-level support files are retained for existing provenance and replay scripts.
In particular, `sequence_partition_validation.json` provides the original raw-input
hash baseline used by the current supplied-sequence validation script. Older
root-level test reports and JSON summaries describe their recorded repository
state; use `feedback_privacy/` for the latest full-suite validation.
