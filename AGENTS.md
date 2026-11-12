# Project instructions

This repository contains an Inspect AI agentic evaluation. Maintain this structure:

- `src/` and dependency file(s): the runnable Inspect evaluation, tools, and scoring code. Keep dependency declarations at the repository root and update them when dependencies change.
- `results/`: evaluation logs and relevant outputs from runs, including at least one actual agent rollout and the evidence used to validate the work.

## Model provider

Use OpenRouter for every new benchmark rollout and model-based judge run. Pass
model IDs with the `openrouter/` prefix. Historical logs and offline test
fixtures are retained as recorded.

## Results and evidence

- Preserve the logs and validation evidence needed to support reported results under `results/`.
- Record the run command, model, relevant configuration, and validation outcome alongside the results so the work can be reproduced.
- Clearly label constructed examples and mocked components. Do not present them as actual agent rollouts or real validation evidence.
- Keep credentials and secrets out of committed code and results.
