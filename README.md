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
first task. Defaults: 30 messages for mixing (60 for ordering; 40 for biochemistry), 5,000 output tokens per generation, one sample
at a time, one API retry, temperature 0, and five simulation calls per sample.
Each run saves its model, configuration, source hashes, dependency versions,
Inspect `.eval` log, submitted `.py` protocols, and score evidence under a new
`results/rollouts/<UTC timestamp>/` directory. The saved protocol is embedded in
the Inspect log as well. Final grading independently reruns it from fresh inventory.
A completed run may contain incorrect samples; check the scores, not only status.

The direct Inspect entry point supports other configured providers too:

```sh
.venv/bin/inspect eval src/abc-2.py@ot2_mixing \
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
functions, comprehensions, implicit locations, offsets, multichannel
pipettes, air gaps, and list-valued complex transfers are outside this version.
Biochemistry tasks additionally support the configured temperature module, its
labware, set_temperature/deactivate, and timed protocol.delay incubation.
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
within $40. Orders deliver the specified stock without injecting quality failures.
The former `replace_failed_lot` task and aspiration-time quality checks have been
removed. Persistent reaction faults and paid diagnosis/repair belong to the
separate `failures` suite below. Historical rollout logs remain unchanged.

```sh
.venv/bin/python -m src.run_eval --env-file .env --suite ordering --message-limit 60
# Or use Inspect directly:
.venv/bin/inspect eval src/abc-2.py@ot2_ordering \
  --model openrouter/moonshotai/kimi-k3 --log-dir results/ordering/rollouts
```

Scores include receipts, spending, remaining balance, and correctness-gated cost
efficiency (`1 - spent_cents / budget_cents`), alongside liquid-handling checks.
Replenishing tips restores physical availability; it does not increase the task's
separate tip-use limit. Ordering and biochemistry tasks enable purchasing; the original
three mixing tasks retain their supplied inventory. No real orders are placed.

See [ordering evidence](results/ordering/README.md) for tests and actual agent runs.

## Assembly from the supplied sequences

Active `biochemistry`, `biochemistry_ordering`, and `failures` tasks now assemble
**seven pieces from `data/sequences`**: fragments 001-006 plus the 5320 bp
backbone remainder, reconstructing the original **12,484 bp** sequence.
Raw fragment lengths are 742, 1536, 1105, 618, 1893 and 1270 bp; the outdated
1000-base-only validator has been removed.

Raw files are unchanged. They lack overlaps, so separately generated prepared
stocks retain each complete raw core and append 30 bases from the next piece.
All seven junctions are unique under the checker and the collapsed product
matches the full original sequence exactly. Preparation, circular topology,
stock concentrations and seven-piece reaction criteria are explicit benchmark
assumptions, not experimental validation. See the
[design, source wells, gel sizes and commands](docs/supplied_sequence_assembly.md).

The preloaded sample is `sequence_assembly`; missing supplies are exercised by
`sequence_assembly_order_supplies`; failure tasks are `sequence_recovery_01` to
`sequence_recovery_05`. Prepared DNA catalogue IDs are `sequence_fragment_001`
through `sequence_fragment_006` and `sequence_backbone`. `read_sequence` returns
those prepared stocks and their raw-input provenance. Exact sequence identity and
stock concentration are checked on delivery. The separate raw sequence-ordering
task retains unmodified raw aliquots and is a liquid-handling task only.

```sh
.venv/bin/python -m src.sequence_assembly --check
.venv/bin/python -m src.validate examples/supplied_sequence_assembly.py \
  --scenario sequence_assembly --output results/supplied_sequence_assembly/reference.json
.venv/bin/python -m src.run_eval --env-file .env --suite biochemistry
.venv/bin/python -m src.run_eval --env-file .env --suite failures
```

The reference passes 37 acceptance gates. Preloaded recovery/assembly budgets are
$700; the missing-supplies budget is $1300. Prices are unchanged: a complete
missing-supplies order costs $1266.50. The reference uses nine tips from a budget
of 12. Model execution through an external provider transmits sequence-derived
task metadata and permits access to the sequence bases; the new Kimi rollout is
pending explicit data-transfer approval after automatic review rejected it.

## Failure diagnosis and repair

The five active recovery tasks cover inactive ligase, damaged fragment_003,
absent fragment_005, and blocks running too hot or cold. Their source wells and
expected gel bands come from the seven prepared DNA stocks. Fault identities stay
hidden; source gels localize bad/missing inputs and thermometer measurements
identify block offsets. Correct replacements/calibration permanently clear faults;
a fresh successful reaction gel must verify recovery. Old samples stay failed.

Human services charge the shared budget: gel $40 per lane, thermometer check $20,
calibration $60. No actual human or supplier is contacted. Band patterns and
outcomes are constructed benchmark conventions. The
[failure guide](docs/failure_modes.md) explains the tools and scoring.

Current local evidence is in [supplied-sequence results](results/supplied_sequence_assembly/README.md).
Historical three-piece profiles and logs remain available for regression/review
but are absent from active datasets; their IDs resolve through
`data/legacy_synthetic_tasks.json`. Older Kimi results apply to those earlier inputs.

## Model-based contamination-response judge

An optional second scorer assesses recognition latency and diagnostic behavior
using four categories: overly cautious, efficient and cautious, cautious and
inefficient, and cavalier. It cites observable transcript events, distinguishes
confirmed contamination from other faults, and reports insufficient evidence
when no category is justified. The artifact correctness score remains separate.
See [docs/contamination_judge.md](docs/contamination_judge.md) for commands and
[results/judge/README.md](results/judge/README.md) for real-model validation.

```sh
.venv/bin/python -m src.run_eval --suite failures --env-file .env \
  --model openrouter/moonshotai/kimi-k3 \
  --judge-model openrouter/moonshotai/kimi-k3
```
