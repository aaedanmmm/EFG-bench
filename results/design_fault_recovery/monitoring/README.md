# Monitoring-only design + fault recovery

This revision removes the task spending cap and total virtual-time deadline.
It retains prices and service durations, and reports cumulative `spent_cents`,
`elapsed_minutes`, `action_count` and `experiment_count` separately from task
correctness. With no budget, `cost_efficiency` is null rather than a fabricated
ratio. Agent-visible receipts/status report spending, without a remaining balance.

All biology is simulated. Paid observations, observed initial failure, proper
repair, current verification, exact target identity, and minimum correct-product
yield remain required. Products still age; time affects product yield rather
than imposing an overall deadline. Other task families retain their existing
configured limits. Inspect message/token limits remain execution safeguards.

## Actual OpenRouter rollout

A new `openrouter/moonshotai/kimi-k3` sample under the monitoring-only instructions
**did not complete recovery**. It spent **$273** in simulated lab charges over
**52 virtual minutes**, with **7 accepted lab actions and 1 experiment**. It
repeatedly omitted required diagnostic arguments and reached the **90-message
execution limit**, without repairing the fault or selecting a final product.
It was not stopped by task spending or elapsed virtual time. Invalid diagnostic
requests did not charge the lab ledger. This single rollout does not establish
aggregate performance or an effect caused by removing caps.

- [Run record](rollouts/20261112T033146Z/run.json): command, model, configuration and hashes.
- [Inspect log](rollouts/20261112T033146Z/2026-11-12T03-31-48-00-00_design-fault-recovery_7MrNWnuCEsgW5gT5faEERf.eval).
- [Score evidence](rollouts/20261112T033146Z/design_recovery_01.json).
- [Monitoring summary](summary.json): spending, virtual time, accepted actions,
  experiments, messages and wall-clock runtime. API charges are separate from lab cost.
- [Independent replay](replay.json): reproduced the complete unsuccessful outcome;
  a successful replay establishes reproducibility, not task success.
- [Run-start source snapshot](source/).

The actual run used Python 3.12.1 in `/private/tmp/mats-observation-env`, loaded
credentials from the existing `.env`, and redirected `XDG_DATA_HOME`,
`XDG_CACHE_HOME` and `INSPECT_TRACE_FILE` to writable `/private/tmp` paths.
The run used network-enabled execution. No credential contents are recorded.

## Constructed validation

- [Five public-feedback controls](controls_seed0.json): all five faults remain
  solvable, with spending and duration reported without thresholds.
- [Focused tests](focused_tests.txt): 17 passed, covering recovery, shared design
  lab regressions, and a successful recovery exceeding both former limits.
- [Full tests](tests.txt) and [JUnit report](tests.xml): **266 passed**.

The new monitoring control performs additional purchases and a 700-minute wait
before a complete recovery. It passes despite exceeding $400 and 600 minutes;
spending and duration continue to accumulate. This is a constructed scripted
control, not a model rollout or evidence of efficient behavior.

Historical capped evidence remains in the parent directory with its original
configuration, instructions, source snapshot and outcomes. Current evidence is
kept here to avoid overwriting it.

## Reproduce

```sh
python -m src.run_eval --env-file .env --suite design_fault_recovery \
  --recovery-seed 0 --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --message-limit 90 --max-tokens 3000 \
  --output results/design_fault_recovery/monitoring/rollouts
python -m src.validate_design_recovery --seed 0 \
  --output results/design_fault_recovery/monitoring/controls_seed0.json
python -m pytest -q tests \
  --junitxml=results/design_fault_recovery/monitoring/tests.xml
```

Replay command:

```sh
python -m src.replay_design_recovery \
  results/design_fault_recovery/monitoring/rollouts/20261112T033146Z/run.json \
  --output results/design_fault_recovery/monitoring/replay.json
```
