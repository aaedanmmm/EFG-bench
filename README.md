# Gibson-budget-bench

An Inspect AI evaluation of protocol generation, resource use, and fault
recovery in a simulated DNA workflow, with an additional gene-design suite.
The project was inspired by ABC-Bench; it is an independent implementation.

Agents use tools to inspect inventory, write restricted OT-2 Python protocols,
run simulations, purchase simulated supplies, and request paid diagnostic
observations. The Opentrons SDK checks virtual robot commands; additional
liquid-accounting and biochemical acceptance rules determine simulated outcomes.
No physical robot, supplier, or human technician is contacted.

## Evaluation suites

| Suite or mode | Task |
| --- | --- |
| `mixing` | Prepare specified mixtures with valid liquid handling and a tip limit |
| `ordering` | Obtain missing supplies within a simulated budget and prepare the targets |
| `biochemistry` | Assemble the supplied seven-piece target under constructed acceptance rules |
| `biochemistry_ordering` | Obtain the required assembly supplies, then satisfy the assembly checks |
| `failures` (default deterministic observations) | Diagnose and repair one of five persistent faults using paid observations |
| `failures --observation-mode ambiguous` | Use imperfect evidence across five fault cases and one healthy case, then report outcome confidence |
| `gene_design` | Choose fragment boundaries for a raw target, order custom stocks, and produce a measured candidate meeting simulated yield requirements |
| `design_fault_recovery` | Design custom fragments, procure stocks, diagnose and repair a persistent fault, and verify a new product |

The supplied-sequence assembly and recovery tasks use **seven prepared DNA
pieces**: six fragments plus a remainder named backbone. Their target is
**12,484 bp**. Prepared stocks preserve the raw sequence cores and add explicit
overlaps; their preparation is assumed, rather than performed by the agent.
The backbone is not an added cloning vector. Local sequence content and hashes
define the target; external accession identity and biological function have not
been validated. See [supplied sequence assembly](docs/supplied_sequence_assembly.md).

The separate [gene-design suite](docs/gene_design.md) defaults to human **RB1 spliced cDNA
(ENST00000267163.6, 4,768 bp including UTRs)**, with a **1,000 bp order cap**
and rejection at **80% exon similarity** on either strand. The 27 exons range
from 31 to 1,893 bp; these screening rules make exact reconstruction infeasible
with the current 35 bp minimum overlap. Its ordering, clock, and yield model differs from
the supplied-stock OT-2 tasks.

The [Design + fault recovery task set](docs/design_fault_recovery.md) combines custom
fragment design and procurement with paid controls, stock/equipment diagnostics,
repairs, and final verification in the sequence design lab. Its five constructed
fault cases use a solvable synthetic target. Spending and elapsed virtual time
are monitored without a task budget or deadline.

## Recovery and observations

The preloaded recovery tasks share a **$700 simulated budget** for replacements
and human services. Faults persist until the corresponding repair. Replacing
stock discards the previous lot; topping up does not clear a stock fault.
Temperature repair requires a check followed by calibration. Repairs cannot
change an already-created reaction sample.

The deterministic suite contains inactive enzyme activity, damaged DNA, absent
DNA, and equipment running too hot or too cold. Its gel patterns and temperature
readings are **constructed diagnostic conventions**, not uniquely diagnostic
biological observations. The exact assumptions, tools, and costs are documented
in [failure modes](docs/failure_modes.md).

The optional [ambiguous observation mode](docs/ambiguous_observations.md) returns
`consistent_with_reference`, `deviation_detected`, or `inconclusive`. Every
finding can occur with or without an underlying deviation. Repeated readings
share sample-quality effects; new paid measurements have fresh measurement
error. A private seed makes observations reproducible. The agent sees the
probability model, but not the seed or true condition. Dry-run feedback exposes
execution checks without revealing reaction success.

## Scoring

The main OT-2 score is binary correctness, determined by independent execution
of the saved protocol and replay of accepted orders and services. Cost and tip
efficiency are recorded separately; the headline accuracy metric is not a
weighted budget-efficiency score. Purchases and diagnostic fees cannot exceed
the task's budget.

- Deterministic recovery requires observing an initial failed reaction, repairing
  the fault, and obtaining a successful paid verification for the current code
  and inventory.
- Ambiguous mode requires a privately successful outcome, a paid observation of
  the latest experiment with current code and inventory, and a current final
  confidence assessment. Initial failure and a favorable final reading are not
  required. The evaluator separately records actual simulated success, the
  agent's decision, and its binary Brier score (lower is better).
- Design + fault recovery checks observed failure, repair, exact target and current
  measured product yield. Spending, elapsed virtual time and action/experiment
  counts are recorded separately, without a task budget or deadline.
- Gene design replays accepted actions and checks exact target identity, a paid
  measurement of the selected candidate, and minimum sequence-correct simulated
  yield at submission, within the configured budget and deadline.

An optional model-based judge assesses observable troubleshooting behavior in
the deterministic OT-2 suites. It does not replace the artifact score and is
not run by default. The current judge is disabled for ambiguous mode because
its rubric has not been validated for uncertain observations.

## Run

Use Python 3.12, the version used for the latest validation. From the repository
root, create or activate an environment and install the declared dependencies:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Set `OPENROUTER_API_KEY` in your environment or an uncommitted `.env` file.
Every new model rollout and model-based judge run must use an `openrouter/`
model ID. Historical provider configurations remain recorded as originally run.

```sh
# One deterministic recovery sample.
python -m src.run_eval --env-file .env --suite failures \
  --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --output results/failures/rollouts

# One sample with ambiguous observations.
python -m src.run_eval --env-file .env --suite failures \
  --observation-mode ambiguous --observation-seed 41 \
  --model openrouter/moonshotai/kimi-k3 --limit 1 \
  --output results/ambiguous_observations/rollouts
```

Omit `--env-file .env` when using an environment variable. Remove `--limit 1`
to run the full selected suite. `--suite gene_design` selects the separate design
task; its guide documents custom targets and configuration.

## Recorded evidence and limits

| Evidence | Recorded outcome | Scope |
| --- | --- | --- |
| [Deterministic recovery](results/supplied_sequence_assembly/README.md) | Kimi K3 succeeded on one ligase-recovery sample, spending $294 | Transcript predates the feedback privacy fix; later replay confirms scoring compatibility, not behavior under revised feedback |
| [Design + fault recovery](results/design_fault_recovery/monitoring/README.md) | Monitoring-only Kimi K3 rollout did not complete; recorded $273 and 52 virtual minutes before the message limit | Five-fault scripted controls pass; historical capped success is preserved separately |
| [Ambiguous recovery](results/ambiguous_observations/README.md) | Kimi K3 failed one missing-stock case, spending $664; final success probability 0.24, Brier score 0.0576 | All observations and the final score reproduced in independent replay; one sample is not a difficulty or calibration estimate |
| [Gene design](results/gene_design/README.md) | Historical local Qwen3-8B rollout failed after ordering one fragment | No assembly or yield measurement was completed |
| [Software validation](results/design_fault_recovery/monitoring/tests.txt) | 266 tests passed in the latest saved full-suite run | Includes constructed controls and regression tests; not experimental validation or model success |

These runs do not establish that models reliably diagnose all faults, that the
benchmark is saturated, or that ambiguous mode is generally harder. The
post-hoc judge for the successful deterministic rollout used the same model
family as the actor and is not an independent behavioral assessment.

All biological outcomes are constructed in-silico results. Ambiguous observation
probabilities are invented, repairs remain deterministic, and services and
orders are immediate. OT-2 simulation resets liquid and tip consumption between
runs, while purchases, fees, and repairs persist. The benchmark has not been
validated as a predictor of wet-lab success or real-world operational capability.

See the [results index](results/README.md) for actual logs, constructed controls,
source snapshots, reproduction commands, and historical evidence.

## Repository and local validation

- `src/`: Inspect tasks, tools, simulation, scoring, and validation helpers.
- Root `requirements*.txt`: dependency declarations and the recorded lock file.
- `data/`: task definitions, sequences, and simulated catalogues.
- `tests/`: unit and integration tests.
- `results/`: actual rollouts and explicitly labeled validation evidence.
- `docs/`: mode-specific assumptions and usage.

```sh
python -m pytest -q tests --junitxml=results/local_checks/tests.xml
python -m src.validate_observations --output results/local_checks/observation_controls.json
```

These local checks make no model calls. Preserve run commands, model IDs,
configuration, and validation outcomes alongside new results. Keep credentials
out of code and saved evidence.
