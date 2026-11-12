# Ambiguous observation evidence

Implementation and usage: [ambiguous observations](../../docs/ambiguous_observations.md).
All observations and outcomes are constructed in-silico quantities. No physical
assay or biological validation has been performed.

## Actual OpenRouter rollout

One real Kimi K3 sample completed under `ambiguous_v1`, observation seed 41.
The actor **failed to recover** the missing-stock fault and scored **0/1**.
It recorded a final success probability of **0.24** and decision
`insufficient_evidence`; the binary Brier score is **0.0576**. That is one
prediction, not an estimate of calibration or aggregate benchmark difficulty.

The actor made four simulated experiments, paid for six categorical sample
measurements and a module check, calibrated the module, and replaced two stocks.
The initial module check was inconclusive, yet the actor calibrated the healthy
module. One intact-stock check produced an adverse finding and the actor replaced
that stock. The actually absent stock remained
unrepaired. Total simulated spending was **$664 of $700**. An attempted source
measurement of the enzyme mix was rejected without charge because source checks
apply to DNA stocks. No model-based judge was used.

- [Inspect log](rollouts/20261109T014352Z/2026-11-09T01-43-53-00-00_ot2-mixing_hgwZVYGJ898euPDQjk5wee.eval)
- [Run command, model, seed, configuration, and source hashes](rollouts/20261109T014352Z/run.json)
- [Generated protocol](rollouts/20261109T014352Z/ambiguous_recovery_01.py)
- [Score evidence](rollouts/20261109T014352Z/ambiguous_recovery_01.json)
- [Verified run-start source snapshot](rollouts/20261109T014352Z/source/)
- [Independent replay](replay.json): all four experiments, all six sample
  measurements, the module check and calibration receipt, final failure, and
  confidence score matched. **A passing replay means faithful reproduction,
  not successful task recovery.**

Run command (the local credential file's contents are never recorded):

```sh
python -m src.run_eval --env-file .env --suite failures \
  --observation-mode ambiguous --observation-seed 41 \
  --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --message-limit 60 --max-tokens 3000 \
  --output results/ambiguous_observations/rollouts
```

The actual interpreter was `/private/tmp/mats-observation-env/bin/python`
(Python 3.12.1), installed from the root dependency files. The local `.venv`
contained no project dependencies. `INSPECT_TRACE_FILE` was redirected to a
temporary file. [environment.txt](environment.txt) records resolved versions.

Two earlier run records, `20261109T014224Z` and `20261109T014256Z`, are setup
failures, not model rollouts. The first could not open Inspect's default trace
file. The second encountered ACP 1.0's removed `acp.helpers` API before actor
generation. Pinning ACP to 0.12.1, already in the repository lock file, resolved
the latter. Neither record contains a completed evaluation or actor transcript.

## Constructed controls and tests

- [tests.txt](tests.txt) and [tests.xml](tests.xml): **243 passed** in the final
  full regression suite, including all existing deterministic tests.
- [focused_tests.txt](focused_tests.txt): 20 uncertainty tests after fixing the
  dependency mismatch.
- [final_focused_tests.txt](final_focused_tests.txt): 46 tests covering uncertainty
  and deterministic recovery, including the additional latest-experiment check.
- [replay_test.txt](replay_test.txt): the observation replay helper accepts valid
  receipts and rejects altered evidence.
- [controls.json](controls.json): 4,000 seeded samples per underlying condition
  match the declared probabilities and shared sample-quality correlation.
- Three adversarial outcome controls use the real SDK: a false reassuring
  observation cannot rescue a failed experiment; an adverse or inconclusive
  observation does not override a privately successful experiment.

The scripted probability baseline's mean Brier scores were **0.13894** using
only the prior, **0.10481** after one observation, and **0.07276** after two
observations with shared quality accounted for. These are constructed binary
inference controls, not model rollouts or optimal repair-policy comparisons.

The run-start snapshot predates a final tightening of current-sample verification:
an ambiguous-mode final measurement must belong to the latest experiment even
when code and inventory match an earlier experiment. The saved actor already
measured its latest experiment, so independent replay under the final code
reproduces its grade. The replay helper was also extended to check source and
module observations explicitly. [validation.json](validation.json) records
source differences, test commands, outcomes, and a credential-value scan.

## Limits

This is an initial controlled uncertainty benchmark. Probability tables are
invented, sample-quality effects are simple, repairs remain deterministic, and
services remain immediate. Confidence concerns binary outcome success; action
optimality and a distribution over fault diagnoses are not scored. The default
deterministic suite and historical logs remain available. One unsuccessful
rollout does not establish a general increase in difficulty or real-world fidelity.
