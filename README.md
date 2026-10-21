# Molecular biology agent evaluation

Project requirements are in [AGENTS.md](AGENTS.md).

## Files

- [src/ctf.py](src/ctf.py): Inspect AI task and agent prompt.
- [src/costs.py](src/costs.py): reagent, consumable, and human-task catalogue.
- [src/fragments.py](src/fragments.py): empty fragment-generation placeholder.
- [src/scorer.py](src/scorer.py): efficiency-scoring placeholder.
- [src/validate.py](src/validate.py): OT-2 protocol-validation placeholder.
- [requirements.txt](requirements.txt): Python dependencies, maintained at the repository root.
- [data/sequences/](data/sequences/): reserved for input sequences; none supplied yet.
- [results/README.md](results/README.md): evidence, validation status, and run-record requirements.

## Setup and evaluation

From the repository root:

```sh
uv venv
uv pip install -r requirements.txt
```

The evaluation is a scaffold. `src/ctf.py` calls an undefined `read_dataset()`;
input sequences, custom scoring, and protocol validation are not implemented.
No successful evaluation or actual agent rollout is claimed.

Once the task is implemented, run it with a configured model and Docker sandbox:

```sh
inspect eval src/ctf.py@intercode_ctf --model <provider/model> --log-dir results/rollouts
```

This is a command template, not an executed run. Keep credentials in the local
environment, outside source and saved evidence. Save the exact command, resolved
model, dependency versions, task parameters, sandbox configuration, and validation
outcome with each run, following [results/README.md](results/README.md).
