# Biochemical scoring evidence

> Historical evidence from an earlier repository state. See the [current results](../../README.md). Original logs, reports and source snapshots are preserved. Paths in reproduction examples reflect the archive layout; original commands remain in the saved run records.

The first profile scores a synthetic Gibson assembly with three linear dsDNA
inputs and a defined 2,340 bp circular target. Outcomes below are **in silico**;
no biochemical experiment was performed.

| Evidence | Origin | Liquid handling | Biochemical acceptance | Experimental outcome |
| --- | --- | --- | --- | --- |
| [Kimi K3 review](../rollouts/20261021T071800Z/gibson_assembly_review/report.md) | Actual Inspect agent rollout | Pass | 21/21 gates passed | Not measured |
| [Reference review](../biochemistry_reference_review/report.md) | Constructed reference protocol | Pass | 21/21 gates passed | Not measured |
| [No-incubation review](no_incubation_review/report.md) | Constructed failing control | Pass | Fail: incubation missing | Not measured |

The actual rollout directory contains its Inspect `.eval` log, `run.json`,
submitted `gibson_assembly.py`, JSON score, and review artifacts. Executed command:

```sh
.venv/bin/python -m src.run_eval --suite biochemistry \
  --env-file ../MATS-work-test/.env --message-limit 40
```

Resolved model: `openrouter/moonshotai/kimi-k3`. One sample, temperature 0,
5,000 output tokens per model call, 40-message limit, five simulation calls
available, and one API retry. Configuration, dependency versions and source
hashes are recorded in the run record. The key is neither copied nor logged.

[validation.json](validation.json) records the final checks and replay under the
final source tree. [Test output](../../biochemistry_tests.txt) and
[JUnit XML](../../biochemistry_tests.xml) are actual test results. Test doubles and
perturbed states are unit-test fixtures, not actual biochemical observations.
The saved actual model submission is replayed through the bounded interpreter
only; native unrestricted Python execution is not required.

See [the scoring guide](../../../docs/biochemistry.md) for interpretation, editing
criteria, and reproduction commands. Existing inert mixing and sequence-linked
liquid-handling rollouts remain valid for their stated scope and do not gain a
biochemical-success claim retroactively.
