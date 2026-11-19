# Monitoring-only rerun with 300 messages

One fresh actual OpenRouter rollout of `design_recovery_01`, recovery seed 0,
using `openrouter/moonshotai/kimi-k3` and a **300-message limit**. The task has
no simulated spending cap or deadline. This is a fresh attempt, not a continuation
of the earlier 90-message run.

## Outcome

The agent **passed**, observing an initial failed target experiment, replacing
the damaged stock and measuring/selecting a new exact-target product. It recorded:

| Metric | Result |
| --- | ---: |
| Simulated laboratory spending | $478 |
| Elapsed virtual time | 149 minutes |
| Accepted laboratory actions | 15 |
| Assembly experiments | 2 |
| Conversation messages | 44 of 300 |
| Model wall-clock runtime | 129 seconds |
| Simulated sequence-correct yield at submission | 87.617 ng |

Laboratory spending is not OpenRouter API cost. Virtual minutes are not model
wall-clock runtime. All biological outcomes and diagnostics are simulated.

The [comparison manifest](comparison.json) confirms that source files and all
recorded configuration settings match the earlier monitoring-only run, except
for the message limit (90 → 300). The earlier run reached 90 messages without
repairing the fault; this attempt completed in **44 messages**, below either
limit. Consequently, this comparison does not establish that raising the cap
caused success. It is one successful rerun of one fault case, not a general
success estimate. The earlier unsuccessful attempt is preserved separately.

## Evidence

- [Run command, model, configuration and source hashes](rollouts/20261112T054950Z/run.json)
- [Actual Inspect log](rollouts/20261112T054950Z/2026-11-12T05-49-51-00-00_design-fault-recovery_Tbb2zkbwZQgt5Wheuiexai.eval)
- [Score and accepted actions](rollouts/20261112T054950Z/design_recovery_01.json)
- [Metric summary](summary.json)
- [Independent replay](replay.json): all score metadata matched
- [Run-start source snapshot](source/)
- [Validation manifest](validation.json)

No benchmark code changed for this rerun. The existing 266-test regression
record remains under [the original monitoring validation](../monitoring/tests.txt).
No model-based judge was used.

## Reproduce

Actual interpreter: Python 3.12.1 in `/private/tmp/mats-observation-env`, with
root dependency files. Credentials were loaded from the existing `.env`, whose
contents are not recorded. Execution used network access and writable temporary
Inspect paths:

```sh
env XDG_DATA_HOME=/private/tmp/mats-design-recovery-data \
  XDG_CACHE_HOME=/private/tmp/mats-design-recovery-cache \
  INSPECT_TRACE_FILE=/private/tmp/mats-design-recovery-300-trace.json \
  /private/tmp/mats-observation-env/bin/python -m src.run_eval --env-file .env \
  --suite design_fault_recovery --recovery-seed 0 \
  --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --message-limit 300 --max-tokens 3000 \
  --output results/design_fault_recovery/monitoring_300/rollouts

python -m src.replay_design_recovery \
  results/design_fault_recovery/monitoring_300/rollouts/20261112T054950Z/run.json \
  --output results/design_fault_recovery/monitoring_300/replay.json
```
