# Incubation feedback privacy fix

The agent no longer receives `qualified_seconds`,
`qualified_incubation_seconds`, the incubation pass/fail check, or its specific
`Biochemistry: <well>.incubation` error. These depend on hidden actual temperature
and could distinguish temperature faults before paid diagnosis. Target incubation
requirements remain public. Private reports, experiment snapshots, paid diagnostic
observations and final scoring retain complete evidence. Redaction also applies
to biochemical dry runs outside the recovery suite.

## Actual local validation

- `focused_tests.txt` / `.xml`: 33 passed, including complete public-response
  equality for all five fault variants with the same public task identity.
- `full_tests.txt` / `.xml`: 189 passed in 105.38 seconds.
- `model_replay.json` / `.txt`: the existing actual Kimi K3 seven-piece recovery
  rollout independently replayed with matching experiment outcomes and final
  score; one successful recovery. No new model generation or API calls occurred.
- `validation.json`: commands, versions, source hashes and validation outcomes.

The new privacy controls use constructed fault scenarios through actual agent
tools and the real SDK. A local Inspect Store fixture supplies sample state;
the simulator is not mocked. These controls are not new model rollouts.
The original actor transcript remains unchanged and contains historical feedback
from before this fix; replay verifies scoring, not behavior under the new feedback.

Commands executed from the worktree root:

```sh
.venv/bin/python -m pytest -q tests/test_feedback_privacy.py tests/test_failures.py tests/test_environment.py --junitxml=results/feedback_privacy/focused_tests.xml
.venv/bin/python -m pytest -q tests --junitxml=results/feedback_privacy/full_tests.xml
.venv/bin/python -m src.replay_failures results/supplied_sequence_assembly/rollouts/20261021T094827Z/2026-10-21T09-48-28-00-00_ot2-mixing_XuViAHXHBhEoKReymvoUdr.eval --output results/feedback_privacy/model_replay.json
git diff --check
```
