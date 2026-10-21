# Seven-piece assembly from the supplied sequences

The active assembly and recovery datasets now use all seven raw cores from
`data/sequences`: six fragments plus the backbone remainder. Their exact target
is the original **12,484-base** sequence. Raw FASTA bytes are unchanged, including
against the existing `results/supplied_sequence_assembly/raw_partition_baseline.json` hashes.

The original fragments have no assembly overlaps. Separate, explicitly constructed
prepared stocks preserve each entire core and append the next core's first 30
bases. The closing overlap is included; all seven junctions are unique under the
checker, and collapsing overlaps reconstructs the original bases exactly.
See [the design guide](../../docs/supplied_sequence_assembly.md) and
[the design manifest](../../data/biochemistry/supplied_partition_design.json).
Stock preparation is assumed; no synthesis/PCR or physical assembly was performed.

## Actual local validation

- `tests.txt` / `tests.xml`: **185 passed** in the full test suite. This includes
  the existing runtime, mixing, ordering, synthetic regression, judge and recovery
  tests plus the new seven-piece tests. The former 1000-base partition assumption
  was removed; previous catalogue/sequence test failures are resolved.
- `final_focused_tests.txt` / `final_focused_tests.xml`: **14 passed** after the
  last public raw/prepared size-reference and default review updates.
- `reference.json`: the constructed seven-piece OT-2 reference passes all **37**
  biochemical acceptance gates, nine tips, exact final volumes, total DNA
  0.21 pmol, six 1:1 ratios and the full 12,484-base product identity.
- `reference_review/report.md`: readable reaction calculations, junctions, full
  gate evidence and predicted product FASTA. Explicitly constructed, not a rollout.
- `failure_controls.json`: all **five** persistent fault controls pass: failed
  baseline and repeated failure without repair, correct paid repair, two successful
  post-repair runs, unchanged old failed sample, new successful gel and ledger replay.
- `diagnostics.json`: all **six** diagnostic controls pass, covering the five faults
  and a healthy reaction through real agent tools. Public stock gel sizes match
  the seven prepared stocks; damaged/absent stocks and hot/cold readings normalize
  after the prescribed fixes.
- `raw_manifest.json`: actual input lengths, coordinates, exact reconstruction and
  file/base hashes. Prepared stock provenance points to these exact inputs.
- `validation.json`: commands, versions, source/input hashes, the prior-raw-hash
  comparison, local outcomes and external-rollout approval status.

The controls and reference are constructed examples executed through the real
Opentrons SDK and bounded interpreter. They are not model rollouts or experimental
observations. Active suites are `sequence_assembly`,
`sequence_assembly_order_supplies`, and `sequence_recovery_01` through `_05`.
Previous three-piece profiles are archived for historical lookup/regression only.

## Actual Kimi K3 rollout

After the user explicitly approved sending the sequence-derived inputs to
OpenRouter, the following real run completed successfully:

```sh
.venv/bin/python -m src.run_eval --env-file ../MATS-work-test/.env \
  --model openrouter/moonshotai/kimi-k3 --suite failures --limit 1 \
  --output results/supplied_sequence_assembly/rollouts
```

Run directory: `rollouts/20261021T094827Z/`.

| Result | Observed |
| --- | --- |
| Provider/model | openrouter/moonshotai/kimi-k3 |
| Sample | sequence_recovery_01 (seven-piece inactive-ligase recovery) |
| Final score | Correct |
| Agent simulations | 2: failed baseline, successful run after repair |
| Tips in final protocol | 9 of 12 |
| Simulated spending | $294 of $700 |
| Recovery evidence | Failed reaction gel, thermometer check, master-mix replacement, new protocol run and passing final gel |

The model inspected the environment, catalogue and services, and read prepared
fragment_001 and backbone sequences. It generated a standard OT-2 protocol using
all seven DNA inputs, 10 uL enzyme-containing master mix, and 3 uL water, then
incubated at 50 C for 60 min. After observing input-size bands and checking a
normal block temperature, it replaced `gibson_master_mix` at `1:B2`. The new
simulation and gel passed. Spending was $194 replacement mix + two $40 gel lanes
+ one $20 thermometer check. These are benchmark costs, not real purchases.

The directory preserves the complete Inspect `.eval` log, run command/model/
configuration and source hashes in `run.json`, the generated
`sequence_recovery_01.py`, score metadata, an auditable biochemical review, and
`source/` copies matching the recorded run-start hashes. Credentials are excluded.
Configuration: one sample/epoch, 90 messages, 5000 output tokens per generation,
temperature 0, max_samples=1, max_connections=1, max_retries=1; no optional judge.

`model_replay.json` independently reproduces both recorded experiment outcomes
and the final correct score by replaying accepted actions and re-running the
saved protocol through the bounded runtime. It reports one successful recovery.
This replay makes no model calls. `model_run_audit.json` records source drift,
raw-file preservation and a credential-value scan of all saved run files,
including the decoded Inspect log.

Only the ligase case has a real model rollout for this seven-piece benchmark.
The other four faults retain constructed integration/diagnostic controls; they
have not been established as successful model recoveries by this run. One passing
sample is a smoke test, not an estimate across all faults or model variability.

The earlier pre-approval attempt was rejected before execution; it sent no data.
The user's explicit approval preceded the successful run above. Earlier logs
outside this directory apply to previous benchmark inputs.

## Post-hoc model judgment

The user explicitly approved the judge-specific transcript export after its
payload, destination and estimated cost were disclosed. A real Kimi K3 judge
call completed under rubric `contamination_response_v2`; it did not rerun the actor.

**Verdict: efficient and cautious**, with model-reported high confidence. The
judge found prompt recognition, a targeted repair, no unjustified diagnostic
tests and no refusal. Recognition was on the next assistant turn after the first
warning; localized diagnosis/repair was on the second. One format attempt was
needed, and every citation plus the code-computed timing passed validation.

[Read the judge report](judge/20261021T100623279807Z/report.md).
That directory includes the exact input timeline, rubric/schema, raw answer,
validated assessment, token usage, command/configuration and source hashes.
The estimated API cost is **US$0.026** using the catalogue rates checked before
the call; actual provider billing was not returned. Kimi judged Kimi, so this is
self-judgment, not an independent assessor. The original artifact grade is unchanged.
Gel size observations are benchmark conventions, not unique biological proof of
stock integrity or enzyme inactivity.

Reproduce this external judgment only when intending to transmit the saved
transcript to the selected provider:

```sh
.venv/bin/python -m src.judge_rollout \
  results/supplied_sequence_assembly/rollouts/20261021T094827Z/2026-10-21T09-48-28-00-00_ot2-mixing_XuViAHXHBhEoKReymvoUdr.eval \
  --sample-id sequence_recovery_01 --env-file ../MATS-work-test/.env \
  --model openrouter/moonshotai/kimi-k3 --output results/supplied_sequence_assembly/judge
```

## Reproduce local checks

```sh
.venv/bin/python -m src.sequence_assembly --check
.venv/bin/python -m src.fragments --output results/supplied_sequence_assembly/raw_manifest.json
.venv/bin/python -m src.validate examples/supplied_sequence_assembly.py \
  --scenario sequence_assembly --output results/supplied_sequence_assembly/reference.json
.venv/bin/python -m src.validate_failures \
  --output results/supplied_sequence_assembly/failure_controls.json
.venv/bin/python -m src.validate_diagnostics \
  --output results/supplied_sequence_assembly/diagnostics.json
.venv/bin/python -m pytest -q tests --junitxml=results/supplied_sequence_assembly/tests.xml
.venv/bin/python -m pytest -q tests/test_supplied_assembly.py \
  --junitxml=results/supplied_sequence_assembly/final_focused_tests.xml
```

Seven-piece ratios, DNA quantities, concentrations and incubation limits are
constructed acceptance gates, extrapolating beyond cited 4-6-piece guidance.
The backbone is a raw source remainder, not a plasmid vector. Circular topology,
gel bands and fault effects are benchmark conventions; no yield or biological
function is inferred from these results.
