# Ambiguous observations

The optional `ambiguous` mode adds imperfect evidence to the existing recovery
suite. The default remains `deterministic`; historical inputs and observations
are unchanged. This is an **abstract probability model**, not a calibrated model
of gels, thermometer accuracy, or experimental biology.

```sh
python -m src.run_eval --suite failures --observation-mode ambiguous \
  --observation-seed 0 --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --output results/ambiguous_observations/rollouts
```

Dependencies remain in the root `requirements.txt` and `requirements-dev.txt`;
no new package is needed. The existing transitive `agent-client-protocol` package
is now explicitly pinned to the lock file's compatible version, 0.12.1, because
Inspect 0.3.282 cannot start with ACP 1.0. `--env-file .env` can load the existing local credential
without recording its contents. All new model and judge calls require OpenRouter.
The existing optional contamination judge is rejected in this mode because its
deterministic rubric has not been validated for uncertain evidence.

## What changes

| Aspect | Deterministic default | Ambiguous mode |
| --- | --- | --- |
| Dataset | Five fault cases | Five fault cases plus one healthy case, with seed-dependent shuffled assignment |
| Dry run | Execution and redacted outcome feedback | Execution feedback only; no reaction success flag or biochemical gates |
| Paid observations | Fixed bands and exact temperatures | `consistent_with_reference`, `deviation_detected`, or `inconclusive` |
| Wording | Branches on the hidden fault | Depends only on the sampled finding |
| Repeat readings | Deterministic | Shared sample quality plus fresh measurement error |
| Initial failure | Must be observed | Not required; healthy cases and prevention are allowed |
| Final verification | Passing paid observation of current protocol/inventory | Paid observation of current protocol/inventory plus private outcome validation; the reading need not be favorable |
| Confidence | Not collected | Final success probability and decision, with separate Brier score |

Public task fields disclose the initial state counts: one healthy, one inactive
activity, one damaged stock, one absent stock, and two equipment-offset cases.
Only IDs differ in the public task definitions; neither the assigned condition
nor the seed is disclosed. IDs do not have a fixed fault mapping across seeds.
Do not use a single repeated seed to claim generalization or fault coverage.

## Observation model `ambiguous_v1`

A private condition is projected into a categorical measurement. For a reaction,
the condition is whether the immutable experiment meets all task gates. For a
source, it is whether that stock has a hidden stock fault or zero nominal volume.
For a module, it is whether its private offset is nonzero. No new biochemical
failure mechanism is introduced.

Twenty percent of samples have a persistent, unobserved quality limitation.
The other eighty percent use the clear-sample probabilities below. The same
abstract channel applies to each kind of measurement.

| Condition and sample quality | Consistent | Deviation | Inconclusive |
| --- | ---: | ---: | ---: |
| Reference match, clear | 0.85 | 0.10 | 0.05 |
| Reference deviation, clear | 0.15 | 0.80 | 0.05 |
| Either condition, limited quality | 0.25 | 0.25 | 0.50 |
| Reference match, marginalized over quality | 0.73 | 0.13 | 0.14 |
| Reference deviation, marginalized over quality | 0.17 | 0.69 | 0.14 |

These probabilities are deliberately constructed. `get_environment` exposes the
complete table and repeat-measurement assumptions so the agent need not infer
undocumented rules. Existing service prices and simulation limits apply.

`src/observations.py` separates three responsibilities:

1. The caller supplies the private condition and sample identity.
2. `measurement` uses independently keyed hash draws for shared sample quality
   and per-measurement error. Neither draw depends on the hidden condition.
3. `present` receives only the finding and measurement ID. It cannot choose
   words based on a fault, seed, true outcome, or sample quality.

Noisy numerical gels and temperature readings are deliberately outside this
first version. Adding noise to those physical quantities would require a separate
empirical validation exercise. The reference sizes remain available as task
metadata; categorical findings do not assert that physical bands were observed.

## Identity, persistence, and replay

- A reaction sample is identified by experiment ID and well. Repairs do not
  alter it. Running a new experiment produces a different sample.
- A source sample is identified by well and delivered lot. Unrelated orders
  do not change its sample quality; replacing its lot produces a new identity.
- Module readings share quality for the module throughout the task, including
  across calibration. Calibration still changes the underlying offset.
- Measurement identity comes from the server-assigned paid service ID, not the
  agent's request ID. Retrying an existing request returns the original report
  without charging or drawing again. A new request produces a new paid reading.
- Version, private seed, scenario, sample identity, and service identity determine
  each draw. Replay does not depend on global random state or process hash seeds.

Private scenario fingerprints remain in trusted evidence, but are removed from
all public assay receipts and account views. Otherwise they could act as a
side channel for guessing the hidden scenario. The final evaluator reconstructs
accepted actions and observations and independently executes the saved protocol.

## Assessment and grading

After the final measurement, the agent calls:

```python
record_assessment(probability_success=0.6, decision="insufficient_evidence")
```

The probability concerns the latest experiment meeting all task conditions.
Decisions are `accept`, `investigate`, and `insufficient_evidence`. The tool
records the belief without returning correctness or a score. The latest
assessment supersedes earlier ones. A subsequent measurement, inventory action,
new experiment, or code change makes it stale; a new final assessment is needed.

The evaluator reports separate quantities:

- `actual_success`: the independently replayed physical acceptance outcome in
  this **simulator**, regardless of noisy observations or assessment completion.
- Overall task correctness: actual success, a valid paid observation of the
  current protocol/inventory, and a current final assessment.
- `calibration.brier_score`: `(probability_success - actual_success)**2`, where
  lower is better. An uncertain decision is permitted and does not itself fail
  the task. Missing or stale assessments are reported as unassessed, not as a
  perfect Brier score.
- `decision`: retained for analysis; no claim that decision optimality is scored.

The run record aggregates actual successes, completed tasks, assessment coverage,
and mean Brier score among assessed samples. A single Brier observation does not
establish calibration: compare many scenarios and seeds, retaining unassessed
coverage and failure rates. This version elicits binary outcome confidence,
not a complete distribution over fault hypotheses or a normative action policy.

## Validation

```sh
python -m pytest -q tests --junitxml=results/ambiguous_observations/tests.xml
python -m src.validate_observations --output results/ambiguous_observations/controls.json
python -m src.replay_failures PATH_TO_ACTUAL_LOG.eval \
  --output results/ambiguous_observations/replay.json
```

The tests include all-state public-feedback equivalence, false reassurance,
false alarms, inconclusive findings, same-sample correlation, observation and
ledger replay, stale assessments, forged receipts, healthy cases, and unchanged
deterministic behavior. Constructed controls and actual model rollouts are
identified separately in [the results record](../results/ambiguous_observations/README.md).
