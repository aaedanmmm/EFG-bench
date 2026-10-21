# Results and evidence

[AGENTS.md](../AGENTS.md) requires actual agent rollouts and validation evidence
to be preserved here. No existing rollout logs were found during reorganization.
The repository does not yet meet the runnable-evaluation or actual-rollout
requirements; moving files does not resolve the implementation gaps.

## Available evidence

- [validation.json](validation.json): actual local structural and syntax checks
  performed after the move, including the command, environment, and outcome.
  These checks do not execute an agent or validate an OT-2 protocol.
- [../src/ctf.py](../src/ctf.py): current evaluation scaffold; dataset loading is
  undefined and the custom scorer and validator are placeholders.
- [../README.md](../README.md): setup and future evaluation command template.

## Recording an actual run

Store Inspect logs under `results/rollouts/`. Alongside each run, save a Markdown
or JSON record containing:

- The exact executed command, date, and code revision or source hashes.
- The resolved provider/model and dependency versions.
- Dataset inputs, task parameters (including attempts and message limit), and
  relevant Docker sandbox configuration.
- Links to the actual Inspect log and any exported transcript or protocol.
- The validation command, its output, and the validation outcome.

Label constructed examples and mocked components explicitly. Never describe a
mock run, syntax check, or unexecuted command as an actual agent rollout. Review
logs for credentials and secrets before committing them.
