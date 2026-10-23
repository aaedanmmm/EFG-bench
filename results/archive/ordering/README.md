# Simulated ordering evidence

> Historical evidence from an earlier repository state. See the [current results](../../README.md). Original logs, reports and source snapshots are preserved. Paths in reproduction examples reflect the archive layout; original commands remain in the saved run records.

> Historical evidence: the failed-lot task and quality mechanism described below have since been removed. See the [current assessment](../failure_system_review/README.md).

The ordering implementation is restored in this worktree. The catalogue, budget,
receipts, quantity/capacity checks, retry handling and paid lot replacement are
real evaluation code. All supply prices and physical stock assumptions are
constructed benchmark values; no supplier or physical robot is contacted.

`tests.txt` and `tests.xml` record the complete test suite for the current setup.
This includes unit tests with explicitly labeled mocks, real Opentrons SDK
integration tests, sequence-file checks and the separate biochemistry tests.

Two synthetic tasks exercise missing supplies and replacement of a faulty first
reagent lot. The actual Kimi K3 run is recorded under
`rollouts/20261021T072202Z/`. Its `run.json` records the provider/model, exact
configuration, dependency versions and source/FASTA hashes. The completed Inspect
log and exported per-sample JSON/protocol files are the authoritative outcomes.
Only the first two synthetic ordering tasks were selected. Their tool catalogue
contains no supplied DNA entries, and their sequence tool rejects access to the
supplied partitions.

Executed from the worktree root:

```sh
.venv/bin/python -m src.run_eval --env-file ../MATS-work-test/.env \
  --suite ordering --limit 2 --message-limit 60 --output results/archive/ordering/rollouts
```

Model: `openrouter/moonshotai/kimi-k3`; one sample at a time, one epoch,
5,000 output tokens per generation, temperature 0, one API retry, five simulator
calls per sample. Budgets: $40 for the missing-supplies task and $55 for the
faulty-lot task. Currency amounts are charged in integer cents. A complete task
needs $37.50 of supplies; replacing the faulty lot costs another $15.

The earlier `rollouts/20261021T071221Z/` log is a real, **cancelled** rollout:
concurrent Git operations removed implementation files while it was running.
No sample finished; it is not claimed as successful validation.

The sequence-ordering task is validated locally in `../sequences/integration.json`.
No external-model rollout of supplied sequences is claimed; data-transfer
approval is pending. `../sequences/README.md` describes the local evidence and
limits. All final scoring reconstructs inventory and charges from accepted order
requests and independently reruns the saved protocol.

## Completed run outcome

Kimi K3 passed both synthetic ordering tasks (2/2):

| Task | Accepted orders | Simulated spending | Remaining | Result |
| --- | ---: | ---: | ---: | --- |
| order_supplies | 4 | $37.50 | $2.50 | Pass |
| replace_failed_lot | 5 | $52.50 | $2.50 | Pass |

`validation.json` records the final test summary, rollout configuration and a
credential/message audit. The audit compares actual model messages against all
supplied sequence bases and sequence/file hashes; none were found.
`kimi_revalidation.json` independently replays both saved protocols using their
recorded purchases through the bounded runtime; both passed. These replay checks
are local and do not call a model.

After the actual run, the ordering default message budget was raised to 60.
The rollout explicitly used 60 already; original `ctf.py` and `run_eval.py` are
preserved in the run's `source/src/` directory for exact reconstruction. The final
test suite was rerun after that default change.
