# Results and evidence

Current assembly/recovery tasks use seven inputs derived from data/sequences. See [current validation](supplied_sequence_assembly/README.md). Older three-piece logs and the failed-lot-removal assessment below describe historical benchmark states.

Current benchmark status after legacy failed-lot removal: [failure-system review](failure_system_review/README.md), including fresh controls and outstanding repository failures.

## Actual model rollout

`rollouts/20261021T065832Z/` contains a completed Inspect evaluation of
`openrouter/moonshotai/kimi-k3` via the user's configured OpenRouter account.
This is real model generation and tool use, not a scripted or mocked model.
All three synthetic tasks passed the independently rerun scorer:

| Task | Result | Tips used | Tip budget |
| --- | --- | ---: | ---: |
| two_reagent_mix | Pass | 3 | 6 |
| three_reagent_panel | Pass | 5 | 12 |
| serial_dilution | Pass | 8 | 12 |

The directory includes the original Inspect `.eval` log, `run.json` with exact
model/configuration/source hashes/dependency versions, and one generated `.py`
plus JSON scoring report per sample. Tool feedback, messages, final liquid
inventories, ledger events, and real SDK robot commands are preserved in the log
and score metadata. The initial rollout used Opentrons 10.1.0's explicit OT-2
virtual-hardware API; its dependency lock is preserved in that directory.

Executed from the worktree root:

```sh
.venv/bin/python -m src.run_eval --env-file ../MATS-work-test/.env
```

Configuration: Kimi K3, all three samples, one epoch, 30-message limit,
5,000 output tokens per model call, temperature 0, max_samples=1,
max_connections=1, max_retries=1, five agent simulation calls per sample.
Credentials remain in the ignored file in the original repo; they are not copied
into this worktree or supplied to the simulation subprocesses. `run.json` records
the equivalent command after credentials have been loaded, omitting their path.

## Final dependency validation

The final runtime is pinned to **Opentrons 8.8.2** because Opentrons 10.1.0's
standard `simulate()` entry point explicitly rejects OT-2 protocols (even though
its explicit OT-2 virtual-hardware API works). This was observed on the constructed
references in `native_reference_validation_opentrons10.json` and is retained as
compatibility evidence, not a failed biological experiment.

- `kimi_revalidation.json`: all three actual model artifacts replayed successfully
  through the bounded interpreter with the final Opentrons 8.8.2 dependency set.
  This is revalidation of real saved submissions, not another model rollout.
- `native_reference_validation.json`: all three constructed references accepted by
  the standard Opentrons 8.8.2 native Python simulator, with its command logs.
  Model-generated code was not executed by this unrestricted entry point.
- `reference_validation.json`: the constructed two-reagent reference validated
  through the bounded runtime during initial implementation with Opentrons 10.1.0.
- `tests.txt` and `tests.xml`: actual pytest results for the final environment.
  Interpreter tests and tool-contract mocks are labeled as such in the test files;
  liquid-handling integration tests use the real SDK, not a mocked `opentrons`.
- `validation.json`: final reproducibility metadata, source hashes, outcomes,
  dependency checks and credential scan outcome.

Reproduce validation from the worktree root:

```sh
.venv/bin/python -m pytest -q tests --junitxml=results/tests.xml
.venv/bin/python results/revalidate.py results/rollouts/20261021T065832Z \
  --output results/kimi_revalidation.json
.venv/bin/python results/check_native.py examples/two_reagent_mix.py \
  examples/three_reagent_panel.py examples/serial_dilution.py \
  --output results/native_reference_validation.json
```

`check_native.py` executes Python through Opentrons' standard entry point. It is
an independent check for trusted, constructed reference files, not an agent tool.
`revalidate.py` uses the bounded interpreter exclusively.

## Earlier setup failures

- `rollouts/20261021T065606Z/run.json`: dependency setup attempt; no model call
  occurred because the OpenRouter integration required a newer OpenAI client.
- `rollouts/20261021T065645Z/`: real model calls reached `get_environment` and
  `write_protocol`, then a first-write workspace bug stopped the sample. The log
  preserves that failed attempt. It is not counted among the three completed
  samples. `test_first_write_and_replacement` covers the fix.

All task inventories and reference protocols are constructed benchmarks. These
results establish success under virtual robot commands and ideal liquid
accounting only. They are not measurements of actual mixing, biochemical
activity, Gibson assembly, or physical OT-2 execution. Three initial tasks are a
smoke test, not a broad estimate of model capability.

## Biochemical scoring extension

The [biochemical evidence index](biochemistry/README.md) records a new actual
Kimi K3 Gibson task rollout, per-gate review reports, final tests, and a
constructed control demonstrating that correct pipetting without incubation
fails the biochemical score. These are in-silico acceptance results; experimental
outcomes remain unmeasured.

## Restored ordering and supplied sequences

See [ordering evidence](ordering/README.md) for the restored budget/order system
and synthetic Kimi K3 rollout. See [sequence evidence](sequences/README.md) for
validated FASTA identities, exact source reconstruction, unchanged input bytes
and a local order-to-simulator check. Historical runs above retain their original
source/dependency records; they do not claim validation of later changes.

## Biochemistry ordering

[Biochemistry ordering evidence](biochemistry_ordering/README.md) records a local
purchase-to-reaction validation, stock/sequence identity checks and 101 passing
tests. The new order-first suite has not been claimed as an actual agent rollout.

## Persistent failure and recovery system

See [failures/README.md](failures/README.md) for five constructed fault controls,
paid diagnostic/repair services, the complete regression results, and real Kimi K3
recovery rollouts. These add a hidden laboratory-state layer to the existing
liquid-handling and biochemical gates. Repair outcomes are synthetic; no actual
human interaction or biochemical experiment was performed.

## Model-based contamination-response judge

[Judge validation](judge/README.md) records the separate assessment of a real
saved failure-recovery transcript, six explicitly constructed rubric controls,
exact evidence/timing, automated checks, and earlier invalid model responses.
The new judge does not replace or alter the protocol correctness score.

## Biochemical checker readability refactor

[Before/after validation](biochemistry_refactor/README.md) records exact report
equivalence across 99 cases, the existing test baseline, and final test outcomes.
