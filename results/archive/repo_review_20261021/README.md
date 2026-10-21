# Repository review, 21 October 2026

> Historical evidence from an earlier repository state. See the [current results](../../README.md). Original logs, reports and source snapshots are preserved. Paths in reproduction examples reflect the archive layout; original commands remain in the saved run records.

Read-only implementation review requested by the user. Only this evidence
directory was added; existing code, results and Git state were preserved.
No new actor/judge API calls were made. A gpt-6-luna subagent independently
reviewed the final rollout evidence and submission requirements.

The current working tree passes all 185 tests (102.53 seconds); see `tests.xml`
and `review_run.json` for the exact command, environment and source hashes.
The current seven-piece actor evidence contains one successful ligase recovery,
not five validated model recoveries. The Luna reviewer inspected the actual
Inspect log and found its stated scope, source provenance and in-silico caveats
consistent with the documentation. `rollout_replay.json` records this review's
fresh local replay of that saved rollout, with no new model generation.

Findings:

1. **Submission blocker: the current Git commit is not the working evaluation.**
   `git archive HEAD` extracted into a temporary directory fails
   `from src.scenarios import load_scenarios; load_scenarios('failures')` with
   `ValueError: Unknown task suite: failures`. See `clean_head.json` for actual
   command/output/revision. Modified `src/scenarios.py` and `src/costs.py`,
   untracked `src/fragments.py`, `src/sequence_assembly.py`, `src/split_sequence.py`
   and untracked final supplied-sequence results are needed for the current
   submission. Additionally, `.git` is a gitfile containing an absolute pointer
   into a sibling checkout, not portable repository history. Commit the intended
   final state and package a standalone repository containing its actual `.git`
   directory; verify the ZIP after extraction outside the original checkout.
2. **Submission blocker: coding/research transcripts are absent.** There is no
   `transcripts/` directory or session index. Inspect actor rollouts and judge
   payloads do not replace the requested coding/research/subagent transcripts.
   Export available sessions, including unsuccessful attempts and this review's
   Luna session, and document unavailable exports in the index.
3. **Evaluation validity: free simulator feedback leaks the temperature-fault
   category.** `src/failures.py:124` removes raw temperatures, but preserves the
   failed incubation gate, its derived seconds, and the incubation error.
   `src/biochemistry.py:429` calculates those fields using the hidden actual
   temperature. With identical correct reference code and no paid services,
   tasks 01-03 report 3600 qualified seconds and a passing incubation gate;
   tasks 04-05 report zero seconds, a failing incubation gate and
   `Biochemistry: 4:A1.incubation`. See `feedback_audit.json`; this is a
   constructed reference control through the actual runtime, not a model
   rollout. Reproduce using `check_feedback.py`. This narrows diagnosis before
   the intended thermometer observation; it does not expose the exact sign or
   magnitude. Keep fault-sensitive derived checks/errors in private evidence and
   expose only programmed incubation facts until measurement. A regression
   should compare the full public feedback across faults, not merely search for
   forbidden fault strings.
4. **Submission framing: README is a technical manual rather than the requested
   2-3 paragraph overview.** It lacks an explicit biosecurity threat model,
   rationale for this capability/proxy, and related-work comparison. Explain
   what autonomous execution/troubleshooting capability is measured, how it
   bears on biosecurity, why a fixed fully specified recipe is an informative
   proxy, and the limits of transferring this result to other tasks. Keep the
   detailed usage documentation elsewhere. One actual current rollout is a
   legitimate smoke test, as already disclosed, but not an estimate across five
   faults or evidence of general biological design ability.

Luna's independent conclusion: final supplied-sequence rollout provenance and
claim boundaries look sound; no coding/research transcript archive or index was
found, README lacks explicit biosecurity/prior-work framing, and `.git` is a
nonportable worktree pointer. This paragraph is a review summary, not an exported
subagent transcript.
