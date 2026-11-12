# Kimi K3 benchmark with default message limits

The run started all seven configurations documented in the project README. Six configurations finished. Ambiguous recovery was interrupted when the user requested a rerun with a shared $10 USD ceiling and no message limit. Inspect saved the first scored ambiguous sample. The actor is `openrouter/moonshotai/kimi-k3`. The task suites ran concurrently, with one active sample and one model connection per suite. Ambiguous recovery uses observation seed 41 to match the earlier single-sample run. The run uses the wrapper's default message and output-token limits, temperature 0, and artifact-based scoring. The optional model judge was disabled.

## Reproduce

From the repository root, install the root dependencies in a Python 3.12 environment and configure the OpenRouter credential in `.env` or the process environment. Point `MATS_EVAL_PYTHON` to that environment's Python interpreter.

```sh
/bin/bash results/kimi_k3_full/run.sh
python results/kimi_k3_full/summarize.py
python results/kimi_k3_full/fetch_billing.py
python results/kimi_k3_full/summarize.py
PYTHONPATH=. python results/kimi_k3_full/replay_scores.py
python -m pytest -q tests --junitxml=results/kimi_k3_full/tests.xml
```

Each timestamped run directory contains the Inspect log, wrapper command and configuration, source hashes, and score artifacts. [summary.json](summary.json) groups artifact grades, token usage, timings, and OpenRouter charges by suite and sample. [generation_billing.json](generation_billing.json) records the provider's billing and timing metadata for the generation IDs in the Inspect logs. API charges are USD and simulated lab spending is recorded separately. All benchmark outcomes are simulated.

The directories `setup_attempt` and `network_attempt` contain startup diagnostics from before any successful OpenRouter response. The first attempt encountered a filesystem restriction at Inspect's default sample-buffer location. The second used temporary storage and encountered the sandbox's network restriction. The rollout records are in the seven top-level suite directories.

## Validation

- [Regression tests](tests.txt) · 243 passed.
- [Score replay](score_replay.json) · Re-executes the benchmark scorers against the artifacts and accepted actions in the saved logs.
