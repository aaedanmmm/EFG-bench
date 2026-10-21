# Failed-lot removal and recovery-system assessment

All work is in `MATS-work-test-worktree`, branch `codex/worktree`. Historical
logs and the other agent's input sequences remain unchanged.

## Removal completed

The old `replace_failed_lot` task is retired. Active task files and the dynamic
sequence-ordering scenario no longer configure faulty deliveries. Ordering no
longer creates usable/unusable flags or schedules bad lots. Aspiration no longer
performs a lot-quality check. Prompts no longer describe that mechanism.
Order IDs remain as provenance; paid stock replacement remains available to
resolve the separate persistent biochemical faults. Their repair path no longer
depends on the removed usable flag.

## Requested changes

| Fault | Implementation | Evidence |
| --- | --- | --- |
| Inactive ligase | Failed reaction with input-size bands below the expected product. Replacing enzyme-containing master mix permanently clears the fault. | Current integration controls/tests; one successful historical Kimi K3 rollout. |
| Fragmented/contaminated DNA | One damaged-DNA state produces a smear/extra bands and loss of the intact stock band. Replace the affected DNA stock. | Current controls/tests; no successful model recovery rollout for this case. |
| Absent DNA | Hidden outcome fault produces two incomplete reaction products and an empty source-stock lane. Replace the associated DNA. | Current controls/tests; no successful model recovery rollout for this case. |
| Incorrect temperature | Separate +12 C and -12 C tasks. Thermometer diagnoses the offset; calibration permanently clears it. | Both variants pass current controls/tests; no successful model recovery rollout for either. |

All five fresh `controls.json` entries pass: failure persists without repair,
two runs pass after the correct repair, old failed reaction samples stay failed,
new reaction gels pass, and accepted actions reconstruct the same costs/state.
Controls execute constructed reference protocols through the real SDK and bounded
runtime. They are not model rollouts or physical measurements.

Each task has a shared $450 budget. Constructed prices: gel $40/lane, thermometer
check $20, calibration $60, enzyme-containing master mix $194, DNA $150/aliquot.
No actual human or supplier is contacted. Final scoring additionally requires a
failed reaction gel before repair and a fresh passing gel for the current code
and inventory. Wrong replacements and topping up do not clear faults.

## Outstanding gaps

1. **Full repository tests: 113 passed, 32 failed, 1 error.** All 25 failure-system
   tests pass. The failures/error are in ordering, biochemical-ordering and
   sequence tests. `fragment_001.fasta` is 742 bases, but `sequence_manifest()` in
   `src/fragments.py` still requires 1000-base numbered partitions. Global
   catalogue loading eagerly validates these unrelated genomic inputs and fails,
   breaking ordinary ordering and biochemical-ordering paths. This mismatch was
   present before failed-lot removal; sequences were preserved. Two new removal
   regressions pass; the repeated-replacement test explicitly isolates the broken
   genomic catalogue while using real catalogue entries and real SDK execution.
2. **Model validation is limited to ligase.** Historical run
   `results/failures/rollouts/20261021T080902Z` completed one real Kimi K3 sample,
   `assembly_recovery_01`, successfully recovering for $294. Earlier real runs
   were cancelled/errored. Controls for other faults do not establish that a
   model independently diagnoses and repairs them. No new model calls were made
   during this assessment.
3. **Strict historical replay has schema drift after removal.** `replay.json`
   records a mismatch: the historical post-order inventory hash includes the
   removed usable=true flag. Current final protocol/biochemical outcomes still
   pass and costs reconstruct to $294, but the final gel's exact hash binding no
   longer matches. `behavioral_replay.json` independently confirms unchanged
   experiment outcomes, liquid contents, fault assessments, public gel
   observations and costs; inventory differs only by removed usable=true fields.
   It is a behavioral comparison, not an exact replay or a new model rollout.
   Archived logs and hashes were not rewritten.
4. **Interpretation differences remain.** A thermometer check only diagnoses;
   repair requires a separate $60 calibration. DNA fragmentation and contamination
   share one damage surrogate. Ambiguous DNA-gel wording was interpreted as loss
   of the intact band plus smear/extra products. The temperature lane is a
   constructed Gibson assembly gel; no PCR amplification/PCR-gel model exists.

Faults gate reaction success until their prescribed repair. Nominal labeled DNA
volumes stay in the liquid ledger even for absent-DNA faults. Bands, smears and
outcomes are deterministic benchmark conventions, not mechanistic biochemistry.

The task entry point was renamed concurrently from `src/ctf.py` to
`src/abc-2.py`; the run wrapper and affected test imports were updated by the
other agent. That change was preserved. `recovery_tests.*` records a final
focused execution after the rename.

## Reproducibility

```sh
.venv/bin/python -m pytest -q tests --junitxml=results/failure_system_review/tests.xml
.venv/bin/python -m src.validate_failures --output results/failure_system_review/controls.json
.venv/bin/python -m src.replay_failures \
  results/failures/rollouts/20261021T080902Z/2026-10-21T08-09-03-00-00_ot2-mixing_Y5egFzQbuVvRXbyAqU2k3z.eval \
  --output results/failure_system_review/replay.json
.venv/bin/python results/failure_system_review/assess_replay.py \
  results/failures/rollouts/20261021T080902Z/2026-10-21T08-09-03-00-00_ot2-mixing_Y5egFzQbuVvRXbyAqU2k3z.eval \
  --output results/failure_system_review/behavioral_replay.json
```

`validation.json` records versions, source/input hashes, commands and outcomes.
`initial_tests.*` retain the first run before the two removal regressions were
isolated from unrelated genomic dependencies. All model artifacts were run only
through the bounded interpreter.
