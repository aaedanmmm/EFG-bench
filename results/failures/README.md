# Failure-mode validation evidence

> Current review after legacy failed-lot removal: [fresh controls, test status and replay compatibility](../failure_system_review/README.md). The results below describe the earlier implementation.

The implementation and diagnostic conventions are described in
[docs/failure_modes.md](../../docs/failure_modes.md). All faults, gel patterns,
stock properties and human-service prices are constructed benchmark assumptions.
No physical robot, enzyme activity assay or real human service was used.

## Deterministic integration controls

[controls.json](controls.json) records five actual local integration controls
through the real Opentrons SDK and bounded protocol runtime. They use the
constructed reference [gibson_assembly.py](../../examples/gibson_assembly.py), not
model-generated code. Each demonstrates an initial failed outcome, another failed
run without repair, the appropriate repair and its charge, two passing runs after
repair, and an unchanged old failed reaction gel after stock/equipment repair.

These controls cover inactive ligase activity, damaged DNA, absent DNA, and high
and low temperature offsets. The source DNA gels and thermometer readings are
explicitly simulated. The control record includes full before/after evidence,
configuration/source hashes, runtime versions, order/service requests and costs.

```sh
.venv/bin/python -m src.validate_failures --output results/failures/controls.json
```

## Tests

[full_tests.txt](full_tests.txt) and [full_tests.xml](full_tests.xml) record an
earlier **125 passing tests**, including the existing evaluation suites and the
new fault system, before the final catalogue-isolation and replacement-tool
changes. [final_tests.txt](final_tests.txt) and [final_tests.xml](final_tests.xml)
record **83 passing tests** for the final focused recovery, biochemical and robot-runtime regressions. Tests cover persistent failures and repairs, wrong/topped-up stock,
multiple simultaneous faults, human fees, shared budgets, invalid requests,
idempotent retries, immutable old samples, stale code/assays, hidden fault labels,
paid-action replay and inventory snapshots during concurrent ordering. Explicit
mock bookkeeping tests are labeled in their source and do not establish robot
or biochemical success.

```sh
.venv/bin/python -m pytest -q tests --junitxml=results/failures/full_tests.xml
```

`tests.txt` / `tests.xml` retain the separate 23-test fault-only run before the
final concurrency regression was added; the final focused suite is authoritative for the completed failure-system changes.

## Actual Kimi K3 runs

The `rollouts/` directories contain real model calls and tool use, not scripted
model outputs. Each `run.json` records the model, parameters, source hashes and
exact command with credentials omitted. The command used the ignored `.env` in
the original repo; credentials were not copied into this worktree or supplied to
simulator processes.

```sh
.venv/bin/python -m src.run_eval --env-file ../MATS-work-test/.env \
  --suite failures --output results/failures/rollouts
```

The first run, `20261021T075836Z`, was interrupted after its first sample reached
the 90-message limit. Kimi obtained a failed reaction gel and a thermometer check,
then repeatedly requested stock lanes without declaring their type. The interface
rejected those calls and the provider exposed empty tool content alongside a
structured error. This was an actual unsuccessful rollout; it is not counted as
successful recovery. Its original modified source files are retained in `source/`.

The interface now infers the lane type from the well address and returns an
explicit error message with `charged=false` for rejected service requests.
`20261021T080144Z` used the corrected lane inference. It was interrupted by a
catalogue/scorer exception after unrelated genomic partition files were changed
concurrently in the shared worktree. Those files were preserved. Recovery tasks
now load only their own synthetic catalogue/sequence data, with a regression
covering unrelated invalid partitions. The model had topped up the suspect mix,
which correctly did not clear its fault. An explicit `replace_reagent` tool now
provides an unambiguous discard-and-replace action.

`20261021T080902Z` is a completed one-sample Kimi K3 smoke run with both
improvements. The model successfully recovered from the ligase fault: it observed
a failed reaction gel, checked the block, replaced the enzyme-containing master
mix, simulated again, and obtained the expected successful reaction gel. Its
final cost was **29,400 cents ($294)**: $194 replacement stock, two $40 gel lanes
and one $20 thermometer check. This run used the revised shared-worktree labour
pricing ($40 gel, $20 check, $60 calibration), preserved in its run source hashes.

[replay.json](replay.json) independently reproduces both recorded experiment
outcomes, the accepted recovery evidence and the final successful score by
reconstructing the action ledger. This is revalidation of actual saved model
artifacts, not another model rollout. Only the ligase case has a successful model
rollout in this change; all five fault cases have constructed integration controls
and tests. [interrupted_replay.json](interrupted_replay.json) records an earlier
replay that correctly reproduced the first run's unsuccessful sample under the
then-current pricing; it does not claim recovery.

To independently replay a completed run and all its saved experiment snapshots:

```sh
.venv/bin/python -m src.replay_failures <path-to-Inspect-log.eval> \
  --output results/failures/replay.json
```

Replay uses the bounded interpreter exclusively and reconstructs stock, repairs
and charges from accepted actions. It performs no new model generation and does
not execute model Python through an unrestricted native entry point.

## Final verification record

[validation.json](validation.json) records final source hashes, package versions,
commands and validation outcomes, current service fees and the result of scanning
this evidence (including decoded Inspect logs) for the configured credential.
The original genomic partition edits were preserved; recovery catalogue loading
is isolated from those inputs.
