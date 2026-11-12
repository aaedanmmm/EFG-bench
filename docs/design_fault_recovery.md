# Design + fault recovery

Run the new task set with `--suite design_fault_recovery` (Inspect entry point
`src/design_task.py@design_fault_recovery`). It extends the **sequence design
lab**, not the OT-2 protocol environment. It connects design, procurement,
experimentation, diagnosis, replacement/calibration, and verification in one
persistent task. No physical robot, supplier or technician is contacted.

## Task set

Five cases share one constructed noncoding **1,382 bp** target. The agent chooses
its fragment boundaries and buys stocks of **300–700 bp**, joining **35–48 bp**
terminal overlaps. At least three stocks are needed. Unlike the default RB1
task, there is no exon screening restriction. There is **no task spending cap or deadline**. Purchases and services retain
their prices and durations; cumulative spending and elapsed virtual minutes are
reported after every action. Final evidence also records action and experiment
counts. The public requirements and prices are
identical across cases; `--recovery-seed` shuffles fault assignment to opaque
sample IDs. The private condition and seed are excluded from public task input.

Exactly one persistent condition affects each case:

| Condition | Evidence that distinguishes it | Repair |
| --- | --- | --- |
| Inactive polymerase lot | Verified-input positive control fails; block reads 50 C | Replace the affected purchased polymerase lot |
| Damaged DNA stock | Control passes; one stock lacks its intact band and has a fragmentation smear | Replace that synthesized stock |
| Absent DNA stock | Control passes; one stock has no detectable DNA | Replace that synthesized stock |
| Block +12 C | Control fails; thermometer reads 62 C at the fixed 50 C setpoint | Check then calibrate |
| Block −12 C | Control fails; thermometer reads 38 C at the fixed 50 C setpoint | Check then calibrate |

The stock fault is bound to the second synthesized stock; enzyme failure is
bound to the first purchased polymerase. These are private construction rules,
not clues supplied to the actor. Binding to agent-created stock IDs allows
arbitrary valid fragment designs. Defective stocks retain their nominal sequence
labels. A fault suppresses simulated product yield rather than causing an order
or execution error. A wrong design can independently give zero yield.

## Agent workflow and tools

The ordinary gene-design tools remain available: status/catalogue, target search,
free quotes, DNA/reagent orders, optional digestion, assembly, yield measurement,
waiting, and product selection. Added tools are:

- `request_design_diagnostic(service="positive_control", polymerase="taq_polymerase")`:
  $40, 20 minutes; supplied verified inputs test the selected purchased enzyme
  on the same block. Control material is not available as target-construction stock.
- `request_design_diagnostic(service="check_stock", fragment_id="dna-2")`:
  $40, 10 minutes; reports intact band length, a fragmentation smear, or absent DNA.
  It does not establish sequence identity.
- `request_design_diagnostic(service="thermometer_check")`:
  $20, 5 minutes; reports actual temperature at the fixed setpoint.
- `request_design_diagnostic(service="calibrate_temperature")`:
  $60, 15 minutes; requires a prior check and clears the module offset.
- `replace_design_stock(fragment_id="dna-2")` and
  `replace_design_reagent(item_id="taq_polymerase")`:
  discard the old lot and buy a verified replacement at the original price.

Normal additional orders do not replace the defective original lot. A replacement
does not modify old reactions or previously digested material. Digested products
inherit source faults, so a replaced precursor must be digested again. All
purchases and services contribute to the same cumulative spending total. Invalid
actions are atomic and do not charge or advance time.

Diagnostics here are deterministic, constructed cues. The existing optional
ambiguous observation channel is not enabled for this suite. The positive
control makes competing causes experimentally distinguishable rather than
relying on repeated generic noisy observations. This still is an idealized
causal model, not calibrated assay physics or a validated wet-lab protocol.

## Scoring and monitoring

Independent replay starts from an empty lab and checks:

1. A paid low-yield observation of an exact-target design affected by the fault,
   obtained while the fault is still active, before repair.
2. Resolution of the injected fault through the corresponding intervention.
3. Selection of the latest experiment using the current inventory revision,
   with its own paid yield measurement.
4. Exact target sequence and at least **40 ng of sequence-correct product at
   submission**. Spending and total elapsed time do not determine correctness.

A control run does not count as the required target experiment. An invalid
fragment design cannot manufacture the initial recovery evidence. Replacing a
stock after measuring the final candidate invalidates that candidate; diagnostics
that do not change inventory do not. Actual confidence calibration is not scored.

The scripted reference uses three fragments (target coordinates 1–500, 461–960,
921–1382) and Taq polymerase. A positive control followed by either source checks
or a module check localizes each fault. All five cases pass, recording **$320–355**
and **167–182 minutes**. These are constructed controls, not model rollouts.

The evaluator reports `spent_cents`, `elapsed_minutes`, `action_count` and
`experiment_count` alongside binary correctness. No cost-efficiency ratio is
calculated without a budget. Costs are simulated laboratory spending, distinct
from any OpenRouter API charges. Virtual minutes differ from model wall-clock
runtime. Existing sample aging still affects product yield: it is a biological
acceptance mechanism, not an overall task deadline. Inspect's message/token
limits remain execution safeguards.

Without a hard cap, a model may replace several components rather than identify
a unique cause. Its recovery can pass, while the additional spending and time
remain visible for comparison. Diagnostic efficiency is therefore an observed
quantity, not a budget-based pass/fail gate. Earlier capped results remain
historical evidence under their original configurations.

## Reproduce

```sh
python -m src.run_eval --env-file .env \
  --suite design_fault_recovery --recovery-seed 0 \
  --model openrouter/moonshotai/kimi-k3 \
  --output results/design_fault_recovery/monitoring/rollouts

python -m src.validate_design_recovery --seed 0 \
  --output results/design_fault_recovery/monitoring/controls_seed0.json
python -m pytest -q tests \
  --junitxml=results/design_fault_recovery/monitoring/tests.xml
```

Use `--limit 1` for a smoke rollout or `--sample-id design_recovery_01` for a
particular sample. No new dependencies are required. See the
[validation record](../results/design_fault_recovery/README.md) for recorded
commands, constructed controls, actual rollout outcomes, and limitations.
