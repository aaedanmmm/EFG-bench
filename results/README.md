# Results and evidence

The current gene design, seven-piece assembly, and ambiguous-observation evidence is indexed below. Historical
runs and intermediate assessments are retained in [archive/](archive/README.md).
All biological outcomes here are constructed in-silico acceptance results;
experimental outcomes have not been measured.

## Current submission evidence

| Folder | Contents |
| --- | --- |
| [ambiguous_observations](ambiguous_observations/README.md) | Optional uncertainty-mode tests, constructed probability controls, and separately labeled OpenRouter rollout evidence |
| [design_fault_recovery](design_fault_recovery/README.md) | Integrated design, procurement, diagnostics and repairs: five-fault scripted controls and one successful actual OpenRouter rollout with independent replay |
| [gene_design](gene_design/README.md) | Gene design rollout and constructed controls for custom synthesis, assembly routes, ordering, and yield |
| [supplied_sequence_assembly](supplied_sequence_assembly/README.md) | Actual Kimi K3 seven-piece ligase-recovery rollout, run configuration/source snapshot, reference, five fault controls, diagnostics, replay, and post-hoc judgment |
| [feedback_privacy](feedback_privacy/README.md) | Subsequent simulator-feedback privacy fix, 189 passing tests, and replay of the saved rollout |
| [judge](judge/README.md) | Judge calibration and refusal controls, with earlier actor-trace assessments identified as historical |

The deterministic seven-piece suite has **one successful ligase-recovery rollout**.
The other four faults have constructed controls, rather than established model
recoveries. That saved actor transcript predates the feedback privacy fix; the
subsequent replay verifies scoring compatibility, not behavior under the revised
feedback. The post-hoc judgment uses the same model family as the actor and is
not an independent behavioral assessment.

The ambiguous-observation mode has **one unsuccessful missing-stock rollout**
from Kimi K3. It spent $664, reported 0.24 probability of success, and received
a binary Brier score of 0.0576. Independent replay reproduced its observations,
experiment outcomes, and score. This establishes a real rollout of the new mode,
not a successful recovery, a calibration estimate, or a controlled comparison
of difficulty. The gene-design folder separately records a failed historical
local Qwen3-8B rollout.

The earlier **3/3 mixing result** belongs to the initial benchmark and is retained
in the [historical results index](archive/legacy_results_index.md). It does not
establish success on all five current recovery tasks.

## Archive and supporting files

[archive/README.md](archive/README.md) indexes the historical folders,
including unsuccessful model attempts. The [relocation manifest](archive/relocation_manifest.json)
maps their original paths to archived paths and records original/current hashes.
Historical logs and evidence retain their original contents, recorded paths,
commands, and source hashes.

The former loose reports and helpers are grouped in
[archive/legacy_root_files/](archive/legacy_root_files/README.md). The original
raw-input hash baseline is preserved beside the current assembly evidence as
[raw_partition_baseline.json](supplied_sequence_assembly/raw_partition_baseline.json).
Regenerating partitions writes `supplied_sequence_assembly/partition_validation.json`
without overwriting that baseline. The latest saved full-suite validation is
[design_fault_recovery/monitoring/tests.txt](design_fault_recovery/monitoring/tests.txt), with **266
passing tests**. `feedback_privacy/` preserves the earlier privacy-fix validation;
new ad hoc checks can write to `results/local_checks/`.
