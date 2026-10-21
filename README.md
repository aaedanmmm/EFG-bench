# OT-2 protocol-generation evaluation

An Inspect AI agent writes ordinary Opentrons Python, tests it on virtual OT-2
hardware, repairs it, and submits the saved protocol. Work is in `src/`; synthetic
task specifications are in `data/`; run logs and validation evidence are in
`results/`. No DNA sequences or wet-lab recipes are required for these mixing
benchmarks.

## Setup

Python **3.12** is required for the tested Opentrons/Pydantic combination.

```sh
uv venv --python 3.12
uv pip install -r requirements-dev.txt
```

`requirements-lock.txt` records the complete tested environment. To reproduce it,
install that file instead. Runtime dependencies are declared in `requirements.txt`;
pytest is in `requirements-dev.txt`.

## Run an agent

Set `OPENROUTER_API_KEY` in your environment or an ignored `.env` file, then run:

```sh
.venv/bin/python -m src.run_eval --env-file .env --model openrouter/moonshotai/kimi-k3
```

The wrapper also recognizes `OPEN-ROUTER_API`, the variable in the existing local
configuration. It loads credentials only into the evaluation process; simulator
subprocesses receive an environment without API keys. `--limit 1` runs only the
first task. Defaults: 30 messages, 5,000 output tokens per generation, one sample
at a time, one API retry, temperature 0, and five simulation calls per sample.
Each run saves its model, configuration, source hashes, dependency versions,
Inspect `.eval` log, submitted `.py` protocols, and score evidence under a new
`results/rollouts/<UTC timestamp>/` directory. The saved protocol is embedded in
the Inspect log as well. Final grading independently reruns it from fresh inventory.
A completed run may contain incorrect samples; check the scores, not only status.

The direct Inspect entry point supports other configured providers too:

```sh
.venv/bin/inspect eval src/ctf.py@ot2_mixing \
  --model openrouter/moonshotai/kimi-k3 --log-dir results/rollouts
```

`intercode_ctf` remains an alias for the scaffold's original entry point.

## Agent environment

Each sample has a separate workspace with four tools:

- `get_environment`: inventory, labware, targets, budgets, and supported API guide.
- `write_protocol`: replace `protocol.py` with complete Python source.
- `read_protocol`: inspect the current saved source.
- `simulate_protocol`: run against fresh inventory and return actionable feedback.

The three constructed tasks cover two-reagent mixing, a three-reagent panel, and
serial dilution. Each specifies stock identity/volume, dead volume, deck layout,
component volumes in target wells, a mixing requirement, and a tip budget.
Scoring requires all component volumes within 0.01 uL, valid handling, explicit
mixing after each final liquid change, and no unintended liquid outside the
specified wells. Serial dilution also requires mixing before sampling.
Scores report success plus tips used and correctness-gated tip efficiency:
`1 - tips_used / (tip_budget + 1)`. This is a diagnostic, not an economic cost model.

## Simulation

```sh
.venv/bin/python -m src.validate examples/two_reagent_mix.py \
  --scenario two_reagent_mix --output results/reference_validation.json
.venv/bin/python -m pytest -q tests --junitxml=results/tests.xml
```

Opentrons is pinned to **8.8.2** for OT-2 compatibility. Version 10 removes OT-2
support from its standard file-simulation entry point.

The simulator uses **the real Opentrons SDK virtual hardware**, not a fake
`opentrons` module. A bounded AST interpreter maps supported Python operations to
SDK calls. It never executes or imports model code, and gives it no shell,
filesystem, network, reflection, or host-process capabilities. Each test runs in a
separate subprocess with a 45-second timeout; Docker is not required. This is a
restricted protocol environment, not a general-purpose Python sandbox.

Supported protocol syntax: an optional `from opentrons import protocol_api`,
literal `metadata` with API level `2.19`, one `run(protocol)` function, assignments,
loops, if/comparisons, literals, indexing, numeric arithmetic, and
`range`/`zip`/`enumerate`/`len`. SDK capabilities include loading the specified
labware/pipette, well lookup, picking/dropping tips, aspirate, dispense, blow_out,
mix, and scalar well-to-well transfer. See `src/environment.py` for exact
signatures and bounds. Unsupported Python or API calls fail explicitly. Helper
functions, comprehensions, implicit locations, offsets, modules, multichannel
pipettes, air gaps, and list-valued complex transfers are outside this version.
Generated files are valid standard OT-2 Python, but only this documented subset
can be graded here.

The additional deterministic ledger tracks per-reagent volumes, homogeneous
mixture sampling, tip capacity, stock depletion/dead volume, well overflow,
conservative contact-based stock carryover, tip reuse, and final mixing. Every
dispense counts as contact, even though real protocols may dispense above liquid.
It does not predict liquid height, residual films, pipetting accuracy, reaction
kinetics, biochemical success, or physical robot safety. Reference protocols in
`examples/` are constructed examples; real model artifacts are stored separately
under `results/rollouts/`.

API references: [Opentrons simulation](https://docs.opentrons.com/python-api/reference/execute-simulate/),
[Inspect custom tools](https://inspect.aisi.org.uk/tools-custom.html).

Initial Kimi K3 results: **3/3 tasks passed**; see [results/README.md](results/README.md)
for the actual rollout, final-version replay, and validation evidence.

## Simulated ordering

Ordering tasks start without stock, tips, or a reaction plate. Agents can inspect
`list_catalogue`, then use `order_supplies(item_id, destination, quantity=1,
replace=False, request_id="")`. Reagent destinations are assigned source wells
such as `1:A1`; consumable destinations are configured deck slots such as `2`
(tips) and `3` (reaction plate). Deliveries are immediate. `get_environment` shows
current stock, receipts, spending, and remaining budget.

Prices and aliquot sizes in `data/ordering_catalogue.json` are synthetic benchmark
values, stored in integer USD cents. Failed orders change neither stock nor budget.
Optional request IDs make identical retries free of duplicate charges. Replacement
discards existing stock or a consumable, charges the full price again, and gives
no refund. Ordering updates the planning inventory; simulations are dry runs and
do not consume it. Final scoring replays accepted requests against the original
scenario and trusted catalogue, then validates the protocol on that inventory.

`order_supplies` requires buying reagent A, water, a tip rack, and a reaction plate
within $40. `replace_failed_lot` has a $55 budget and a deterministic faulty first
reagent A lot. Lot quality is revealed during simulated aspiration, requiring a
paid replacement. This models a synthetic quality failure, not biochemical activity.
The failure schedule is hidden from the agent prompt and inventory tools.

```sh
.venv/bin/python -m src.run_eval --env-file .env --suite ordering --message-limit 40
# Or use Inspect directly:
.venv/bin/inspect eval src/ctf.py@ot2_ordering \
  --model openrouter/moonshotai/kimi-k3 --log-dir results/ordering/rollouts
```

Scores include receipts, spending, remaining balance, and correctness-gated cost
efficiency (`1 - spent_cents / budget_cents`), alongside liquid-handling checks.
Replenishing tips restores physical availability; it does not increase the task's
separate tip-use limit. Only the two ordering tasks enable purchasing; the original
three mixing tasks retain their supplied inventory. No real orders are placed.

See [ordering evidence](results/ordering/README.md) for tests and actual agent runs.
