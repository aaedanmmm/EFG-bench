# Design + fault recovery evidence

This task set combines custom fragment design and procurement with persistent
fault diagnosis, repair and verification. All biological outcomes, diagnostic
cues and services are constructed simulations. See
[task documentation](../../docs/design_fault_recovery.md).

## Current monitoring-only configuration

The current task set has no task budget or deadline. It records spending, elapsed
virtual time, action count and experiment count separately from correctness.
The [monitoring validation record](monitoring/README.md) covers this revision.
All earlier artifacts below preserve the original $400 / 600-minute settings;
they are not evidence of model behavior under the revised instructions.

## Historical capped OpenRouter smoke rollout

One actual `openrouter/moonshotai/kimi-k3` rollout completed on
`design_recovery_01`, recovery seed 0, with 90 messages and at most 3,000 output
tokens per generation. The agent **passed** the damaged-stock case. It designed
three fragments, chose Taq, measured an initial failed target experiment, checked
temperature, ran a positive control, checked two stocks, replaced the damaged
stock, and measured/selected a new reaction. It spent **$375 of $400**, used
**187 virtual minutes**, and submitted **71.264 ng** of sequence-correct product
under the simulator's private yield model. One sample does not establish recovery
across all five faults or general diagnostic competence. No model judge was used.

- [Run command, configuration and source hashes](rollouts/20261112T012616Z/run.json)
- [Actual Inspect log](rollouts/20261112T012616Z/2026-11-12T01-26-16-00-00_design-fault-recovery_GRnJWeGeFLnYdBNAhhtu62.eval)
- [Scoring evidence and accepted actions](rollouts/20261112T012616Z/design_recovery_01.json)
- [Independent replay](replay.json): reconstructed all actions and reproduced the
  complete score metadata; recorded source hashes matched.
- [Source snapshot](source/): Python, scenario data, sequence inputs and root dependencies.

Earlier records `20261112T012522Z` (Inspect sample-buffer write permission)
and `20261112T012540Z` (network connection failure) are unsuccessful setup
attempts, not completed model rollouts. Their logs and consoles are preserved.
The completed run redirected Inspect trace, cache and data directories to
`/private/tmp` and used network-enabled execution. Credentials were loaded from
an existing local `.env`; their contents are not recorded.

Actual run command (Python 3.12.1 in `/private/tmp/mats-observation-env`):

```sh
env XDG_DATA_HOME=/private/tmp/mats-design-recovery-data \
  XDG_CACHE_HOME=/private/tmp/mats-design-recovery-cache \
  INSPECT_TRACE_FILE=/private/tmp/mats-design-recovery-trace.json \
  /private/tmp/mats-observation-env/bin/python -m src.run_eval --env-file .env \
  --suite design_fault_recovery --recovery-seed 0 \
  --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --message-limit 90 --max-tokens 3000 \
  --output results/design_fault_recovery/rollouts

python -m src.replay_design_recovery \
  results/design_fault_recovery/rollouts/20261112T012616Z/run.json \
  --output results/design_fault_recovery/replay.json
```

## Constructed controls

[Seed 0](controls_seed0.json) and [seed 41](controls_seed41.json) contain five
passing scripted recovery workflows each. They use a known reference design and
choose repairs from public diagnostic responses, without reading the hidden
fault. Each records an initial failure, repair and final success. Spending is
**$320–355**; elapsed time is **167–182 minutes**. These establish solvability in
the simulator, not model performance or wet-lab validity. Fault assignment alone
is shuffled by seed; the target and deterministic fault mechanisms are unchanged.

The positive-control policy is a feasibility baseline, not an optimal policy.
A blanket replacement of three stocks, the cheapest enzyme and calibration
would require $460 including initial procurement and required yield assays,
exceeding the $400 budget. This excludes that particular blanket strategy.

[Regression results](tests.txt) and [JUnit report](tests.xml) record **265 passing
tests** in the final full-suite check. New tests cover all five faults across three seeds, identical
public task definitions, feedback privacy, incomplete/stale verification, wrong
target designs, control interpretation, top-ups versus replacement, inherited
digest faults, and atomic rejected services. No new dependencies were added.

[Validation manifest](validation.json) records commands, run-start source-snapshot
verification and a clean credential-value scan of text artifacts and parsed Inspect logs.
