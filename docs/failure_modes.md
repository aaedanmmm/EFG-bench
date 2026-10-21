# Persistent failure and recovery benchmark

Current active tasks use **seven data/sequences-derived DNA pieces**, with a 12,484 bp target. See the [current design and configuration](supplied_sequence_assembly.md). Current gel sizes and source wells are listed in that guide; old three-piece results remain archived.

The legacy aspiration-time failed-lot system has been removed. This reaction-fault suite remains active. See [current seven-piece validation](../results/supplied_sequence_assembly/README.md); the earlier failed-lot-removal assessment is historical.

The `failures` suite adds five constructed troubleshooting tasks to the existing
OT-2 assembly evaluation: inactive ligase activity in the enzyme-containing master
mix, damaged/contaminated DNA, an absent DNA input, and a block running either
12 C above or 12 C below its programmed temperature. The public task names and
instructions do not disclose the injected fault. Stocks start preloaded; the
agent has a shared $700 budget for replacements and human services.

```sh
.venv/bin/python -m src.run_eval --env-file ../MATS-work-test/.env \
  --model openrouter/moonshotai/kimi-k3 --suite failures \
  --output results/failures/rollouts
```

Direct Inspect entry point: `src/abc-2.py@ot2_failures`. The default message limit
is 90 and each task permits eight protocol simulations.

| Fault | Constructed observation | Effective repair |
| --- | --- | --- |
| Ligase activity fails | Reaction lane has multiple bands below the expected product; DNA stock lanes look intact | Replace the enzyme-containing `gibson_master_mix` at 1:B2 with `replace=true` |
| Damaged/contaminated DNA | Reaction lane has a low-size smear or extra products; the affected stock lane lacks its intact expected band | Replace that DNA stock with `replace=true` |
| Absent DNA | Reaction lane has two large incomplete products; the affected DNA stock lane has no detectable band | Replace the specific missing DNA stock with `replace=true` |
| Temperature block too hot/cold | Reaction has weak incomplete products despite nominal incubation; a thermometer reveals the difference between requested and measured temperature | Request a human thermometer check, then human calibration |

The DNA-damage wording is interpreted as absence of the **expected intact band**,
with fragmentation smear or multiple products. The missing-DNA two-product
pattern is an explicit user-requested benchmark convention. Neither it nor any
other pattern is claimed to follow uniquely from real assembly chemistry.
Reaction sizes use a hypothetical linearized-product diagnostic lane; real
circular DNA migration cannot be inferred from nominal base-pair length alone.
The synthetic bands and smear ranges are deterministic cues, not physical
predictions, measured gels, yield estimates, or diagnostic recommendations.

## Diagnostic sizes visible to the agent

`get_environment` exposes a public `diagnostic_reference`: source wells and
expected intact DNA sizes for all seven prepared stocks (772, 1566, 1135, 648,
1923, 1300 and 5350 bp), the expected 12,484 bp product, and the acceptable incubation range. This reference
is identical whether a hidden fault is present or absent. `run_gel` reports
numerical `bands_bp` and `smear_range_bp` in base pairs for the requested lane.

A reaction gel flags incomplete assembly but may not localize the fault. Request
individual stock lanes to identify a missing intact band or a damaged stock's
smear/smaller products. Existing missing-DNA reaction sizes are synthetic cues,
not partial-product lengths computed from the missing component. Enzyme failure
and temperature failure share input-size reaction bands; use a thermometer to
distinguish an out-of-range block. At a 50 C setpoint the hot/cold tasks report
62 C / 38 C, while normal and calibrated blocks report 50 C. A gel alone cannot
establish whether a block is hot or cold. Normal stock lanes and a normal block
narrow the problem but do not uniquely prove enzyme inactivity in real biology.

[Diagnostic-observability evidence](../results/diagnostic_observability/README.md)
contains six actual tool-executed constructed controls and 39 passing tests,
including localization from public observations with faults rotated across all
three DNA inputs. No new model recovery claims are made.

## Tools and costs

The new tools are `list_human_services`, `request_human_service` and
`replace_reagent(item_id, destination)`. The last explicitly discards suspect stock
and purchases a new lot, avoiding confusion with a top-up order. Gel lane
type defaults to `auto`, inferred from the source or reaction well address.
Rejected service requests return an explicit error and `charged=false`. All services
are immediate simulated human actions: no actual person is messaged and no
external purchase takes place. Costs are constructed USD prices, not live quotes.

Service prices are technician labour: estimated occupied technician hours x an
assumed fully loaded rate of $40/h (wage plus benefits and overhead, roughly
1.4-1.6x a ~$25-30/h US lab-technician wage). Hours include setup and cleanup
but not unattended instrument time; consumables are not charged. The rate is
`TECHNICIAN_RATE_CENTS_PER_HOUR` in `src/failures.py`.

| Service | Technician time | Cost | Effect |
| --- | ---: | ---: | --- |
| `run_gel` | 1.0 h (cast, load, run, image, clean up; ~1.5 h elapsed) | $40 per lane | Tests the latest reaction sample or the current stock in a specified DNA source well |
| `thermometer_check` | 0.5 h (probe, equilibrate, record) | $20 | Returns setpoint, measured temperature and offset; changes no equipment state |
| `calibrate_temperature` | 1.5 h (multi-point check, correct, re-verify, document) | $60 | Requires a prior thermometer check on that module, then permanently clears its offset |

Example service calls:

```python
request_human_service(service="run_gel", sample="4:A1", sample_type="reaction")
request_human_service(service="run_gel", sample="1:A3", sample_type="source")
request_human_service(service="thermometer_check", module_slot="4", setpoint_c=50)
request_human_service(service="calibrate_temperature", module_slot="4")
```

Use `replace_reagent` for repairs, or `order_supplies(..., replace=true)`.
Replacement stock prices come from `list_catalogue`: synthetic enzyme mix $194,
DNA $150 per aliquot. All orders and services debit the same integer-cent ledger.
Invalid requests, impossible assays and over-budget actions are atomic and do
not charge. Optional request IDs make identical retries idempotent; reusing a key
for different arguments fails. Retrying a gel ID returns the **old observation**,
so a fresh measurement needs a fresh key.

## State and scoring

Silent faults do not cause an aspiration error: the nominal liquid accounting
can pass while the constructed assembly outcome fails. DNA contents and volumes
in the liquid ledger represent labeled stock aliquots; hidden quality/absence
state determines whether those labels deliver functional DNA in the outcome
model. This layer does not alter the nominal FASTA sequence or pretend a missing
physical molecule has been observed.

Faults persist across every simulation. Reordering an unrelated stock or topping
up affected stock leaves its fault active. Only replacement of that specific
stock with a good lot clears it. A thermometer measurement diagnoses but does
not calibrate. Changing the programmed setpoint cannot satisfy the equipment
repair requirement. Calibration corrects the hardware offset; the saved protocol
still has to meet the normal incubation gates afterward. Multiple configured
faults require all applicable repairs.

Simulations consume fresh virtual aliquots and tips, as in the existing planning
environment; purchases, diagnostic charges and equipment/reagent states persist.
Each simulation creates a new immutable experiment snapshot. Repairing stock or
equipment does not repair an old reaction. To demonstrate recovery the agent
must obtain a failed reaction gel **before** repair, apply the appropriate fix,
simulate again, and obtain a passing gel for the current saved code and stock.
Editing code or replacing stock after that gel invalidates its final-verification
role, even when the edited protocol would execute correctly.

The final scorer reconstructs all orders and human services from the original
private scenario and trusted catalogue. It ignores mutable inventory and cached
pass flags, independently executes the current code, and checks paid gel
observations against experiment snapshots and action history. Overall success
requires liquid handling, biochemical acceptance, no unresolved fault, observed
initial failure, and current successful verification. Full fault identities are
retained in evaluator evidence but removed from agent tool feedback.

Implementation: `src/failures.py`, integrated with `environment.py`, `ordering.py`,
`simulator.py` and `scorer.py`. Task configuration is `data/failures_tasks.json`.

The pre-existing assembly gates use [NEB's assembly guidance](https://www.neb.com/protocols/gibson-assembly-protocol-e5510).
The gel symptoms, offset magnitudes, repair rules and service prices in this
suite are additional constructed benchmark assumptions.
