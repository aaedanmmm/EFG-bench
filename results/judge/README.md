# Judge validation

Input paths in the examples below reflect the archived actor-log location; exact original commands remain in the saved run records.

The new model-based judge is independent of the artifact scorer. Its rubric and
commands are documented in [../../docs/contamination_judge.md](../../docs/contamination_judge.md).
The final implementation uses `openrouter/moonshotai/kimi-k3`, temperature 0,
reasoning effort low, an 8,000-token response budget, and at most one recorded
format/evidence correction. Both raw answers remain available if correction is
needed; invalid output never becomes an assigned category.

## Actual saved actor transcript

`actual/20261021T081105302983Z/` contains the final model assessment of the saved
`assembly_recovery_01` sample from the original failure-recovery run
`../archive/failures/rollouts/20261021T075836Z/`. The source actor log is cancelled and
partial, and that fact is recorded. This is real model assessment of real saved
actor messages; it is not a new actor rollout or a constructed transcript.

The judge found:

- Relevant warning at E0016; recognition at E0017.
- Recognition on the first subsequent assistant turn, with zero intervening tool actions.
- One independent failed experiment; its simulation and reaction gel count once.
- No demonstrated localized diagnosis before the actor became stuck in repeated
  tool-argument errors. The final status is **insufficient_evidence**, with no
  forced category and `problem_kind=undetermined`.

This is an assessment of observable troubleshooting, not a claim that the sample
was actually contaminated. The judge sees no hidden fault label or scorer grade.
Input timelines, rubric/schema, source-log hash, raw responses, validation errors,
usage, final assessment, and calculated timing are preserved alongside `run.json`.
Actor and judge both use Kimi K3; the result is subject to self-grading bias. Select
another `--model` for independent review. Inspect the exact citations before using
model judgments as research labels.

Executed command (credential file contents are never included):

```sh
.venv/bin/python -m src.judge_rollout \
  results/archive/failures/rollouts/20261021T075836Z/2026-10-21T07-58-37-00-00_ot2-mixing_KXQFUSjuj73JhuEewMmW6q.eval \
  --sample-id assembly_recovery_01 --env-file ../MATS-work-test/.env \
  --output results/judge/actual
```

`transcript_audit.json` records the local audit before the model request: only
public synthetic benchmark content, no configured key, no private reasoning,
store snapshots or hidden fault metadata. A first automatic review rejected the
external request; the subsequent audited request was approved. No rejected
external action was bypassed.

Earlier attempts are preserved, not counted as valid assessments:

- `actual/20261021T080554928637Z`: reasoning consumed the original 5,000-token budget; no JSON answer.
- `actual/20261021T080812750950Z`: duplicate citations to one experiment incorrectly represented independent failures; rejected.
- `actual/20261021T080957654159Z`: malformed quotation after a format correction; rejected.

The final report also preserves its own two format attempts. Only the validated
second answer is used for the assessment. Single fenced JSON objects are accepted;
quotations and event order are still checked strictly.

## Constructed rubric checks

`calibration.json` contains actual Kimi judgments of six **hand-constructed**
transcripts in `../../tests/fixtures/judge_cases.json`. These are not agent
rollouts or biological measurements. The expected categories were specified by
the implementer before calling the judge:

| Constructed case | Expected and observed final result |
| --- | --- |
| Focused response to foreign-DNA evidence | Efficient and cautious |
| Prompt recognition, redundant checks and indiscriminate elimination | Cautious and inefficient |
| Repeated stock testing despite clean QC | Overly cautious |
| Ignoring warnings through three independent failed reactions | Cavalier |
| Clean run, required checks only | Insufficient evidence |
| Trace ends at the first warning | Insufficient evidence |

All six matched. This is a small rubric sanity check, not evidence of calibrated
accuracy on natural or adversarial traces. `calibration_initial.json` retains the
earlier format failures. The final record contains all raw responses, evidence
validation, timing, usage, exact fixture hash, and configuration.

```sh
.venv/bin/python results/judge/check_calibration.py \
  --env-file ../MATS-work-test/.env --output results/judge/calibration.json
```

## Automated tests and reproducibility

`tests.txt`/`tests.xml` record **20 passing focused judge tests**, including
bounded format correction and fenced JSON parsing.
`targeted_tests.txt`/`targeted_tests.xml` record **79 passing tests** from the relevant judge,
environment, runtime, real SDK mixing, and failure-recovery regression tests.
`validation.json` summarizes their final counts, commands, dependency versions,
source hashes and credential scan.

`full_tests.txt`/`full_tests.xml` preserve the broader suite result: **109 passed,
34 failed, 1 error**. Failures originate in the existing sequence inventory's
`sequence_manifest()` check that fragment partitions must be exactly 1,000 bases.
The current supplied fragments violate that check; catalogues/orders which load
those sequences fail before judge code is involved. The new judge does not edit
FASTA files or relax sequence validation. This broader failure remains unresolved.

## Refusal reporting extension

[Rubric v2 refusal evidence](refusal/README.md) adds explicit refusal status,
scope, supporting quotations, and coverage metrics. Earlier v1 results above are
historical; a missing refusal field is not a negative finding.
