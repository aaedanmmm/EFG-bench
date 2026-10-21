# Biochemistry ordering integration

> Historical evidence from an earlier repository state. See the [current results](../../README.md). Original logs, reports and source snapshots are preserved. Paths in reproduction examples reflect the archive layout; original commands remain in the saved run records.

The biochemical task now has its own sequence-aware ordering path. Input items
are `gibson_backbone`, `gibson_insert_A`, and `gibson_insert_B`, read from the
separate records in `data/biochemistry/synthetic_gibson.fasta`. They are distinct
from the supplied partitions in `data/sequences/`; in particular, the two items
with component name `backbone` cannot be substituted across tasks.

The catalogue also supplies `gibson_master_mix` (declared 2X stock), water,
compatible tips and `temperature_reaction_plate`. DNA stock concentrations are
copied from the biochemical specification. Delivery rejects identity or stock
concentration mismatches before charging. Both normal deck labware and module
labware must be purchased when unavailable. Final scoring replays the purchases
and runs all the existing liquid-handling and biochemical acceptance gates.

## Actual local evidence

- `validation.json`: actual local validation using constructed order requests and
  `examples/gibson_assembly.py`. All seven orders succeeded for a simulated
  $666.50 out of a $700 budget. The protocol passed with five tips, including all
  21 biochemical acceptance checks. This is **not an agent rollout** and no
  biochemical or physical experiment was performed.
- `validate.py`: reproduces the purchase-to-score check without model calls.
- `tests.txt` and `tests.xml`: 101 actual passing tests across the project.
  New cases cover multi-record sequence lookup, backbone substitution rejection,
  exact stock concentrations, receipt replay, missing module labware, and failure
  of biochemical gates even when purchasing and liquid handling succeed.

Commands from the worktree root:

```sh
.venv/bin/python results/archive/biochemistry_ordering/validate.py
.venv/bin/python -m pytest -q tests --junitxml=results/archive/biochemistry_ordering/tests.xml
```

For a future agent rollout, the order-first task is available as:

```sh
.venv/bin/python -m src.run_eval --env-file .env --suite biochemistry_ordering
# Or:
.venv/bin/inspect eval src/ctf.py@ot2_biochemistry_ordering \
  --model openrouter/moonshotai/kimi-k3 --log-dir results/archive/biochemistry_ordering/rollouts
```

These are invocation examples, not newly executed model runs. The original
`biochemistry` suite remains preloaded and can now optionally restock from the
same validated catalogue. Purchasing does not bypass sequence/stoichiometry,
mixing or incubation requirements. The acceptance model reports experimental
status as `not_measured`; no yields or biological activity are inferred.
