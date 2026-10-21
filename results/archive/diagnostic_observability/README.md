# Can an agent infer problems from diagnostic observations?

> Historical evidence from an earlier repository state. See the [current results](../../README.md). Original logs, reports and source snapshots are preserved. Paths in reproduction examples reflect the archive layout; original commands remain in the saved run records.

Yes, using the configured public observations and appropriate follow-up assays.
The final reaction gel does not uniquely diagnose every cause; source-stock lanes
localize DNA problems and a thermometer identifies a hot or cold block.

## Public size reference

`get_environment` now includes `diagnostic_reference`, derived only from declared
FASTA inputs, expected product and source-well mapping, independently of hidden
fault state. It includes units, expected sizes and diagnostic limits.

| DNA input | Source well | Expected intact band |
| --- | --- | ---: |
| Backbone | 1:A1 | approximately 1000 bp |
| Insert A | 1:A2 | approximately 600 bp |
| Insert B | 1:A3 | approximately 800 bp |
| Complete reaction product | 4:A1 | approximately 2340 bp |

`run_gel` returns numerical `bands_bp` and optional `smear_range_bp`, not merely a
pass/fail label. Each lane identifies its sampled well, and stock lanes identify
the component and its expected intact band. The synthetic sizes are approximate
benchmark estimates; the observations are not measured gels.

## Observations actually returned by the tools

The six controls in `observations.json` call the same environment, simulation and
paid service tools used by the model. Their SDK runs and service responses are
real executions of the benchmark; no tool/SDK result is mocked. They are
constructed controls with a programmed repair policy, not model rollouts.

| Condition | Reaction gel bands, bp | Relevant source lane | Thermometer at 50 C |
| --- | --- | --- | --- |
| Healthy | 2340 | Intact 1000, 600 and 800 bp stock lanes | 50 C |
| Inactive ligase | 600, 800, 1000 | All three stock lanes intact | 50 C |
| Damaged insert A | 585, 1287 plus smear | 168 and 366 bp bands; smear 30-480 bp, missing intact 600 bp band | 50 C |
| Absent insert B | 1404, 1919 | No detectable band in the stock expected at 800 bp | 50 C |
| Block too hot | 600, 800, 1000 | All three stock lanes intact | 62 C |
| Block too cold | 600, 800, 1000 | All three stock lanes intact | 38 C |

The missing-DNA reaction bands remain the existing constructed two-product cue,
not sequence-derived partial-assembly lengths. Those bands alone cannot tell
which input is absent. Individual source lanes provide that localization.
Likewise, the damaged-DNA reaction smear flags a problem but stock lanes identify
which input is damaged. Identical-size inputs cannot be distinguished by size in
a pooled lane; source well identity would still distinguish separate stock lanes.

The enzyme and heat-fault reaction gels have the same band sizes. This ambiguity
is intentional and explicitly tested: source gels plus a thermometer are needed.
A normal thermometer and intact sources narrow a failed reaction to an
enzyme/other reaction problem; they are not unique biological proof of ligase
inactivity. The gel alone never establishes whether a block is hot or cold.

After replacing damaged/absent DNA, the affected stock lane returns to its intact
expected size. After calibration, the block reads 50 C at a 50 C setpoint.
After the correct repair and a new protocol run, all five fault controls produce
a single 2340 bp reaction band. The old failed reaction sample stays unchanged,
as covered by the existing recovery tests.

## Validation and limits

- `tests.txt` / `tests.xml`: **39 passed** (14 diagnostic-observability checks and
  25 existing recovery tests).
- The localization tests rotate both absent and damaged faults through all three
  DNA pieces, then infer the affected component from public source-lane
  observations. They do not read fault labels or rely on case IDs to diagnose.
- Negative controls have healthy DNA and normal temperature readings; they do
  not falsely indicate stock damage/absence or a heat-block fault.
- `observations.json`: all five fault controls plus a healthy control, full public
  environment/tool receipts, real SDK commands, inferred observable summaries,
  repair observations, costs, versions and source hashes.
- No new model rollout was performed. The controls establish that diagnostic
  information is present, not that every model uses it correctly.
- This was focused verification. The unrelated full-suite sequence/catalogue
  failures documented in `../failure_system_review/README.md` remain outside
  this change.

Commands from the worktree root:

```sh
.venv/bin/python -m pytest -q tests/test_diagnostics.py tests/test_failures.py \
  --junitxml=results/archive/diagnostic_observability/tests.xml
.venv/bin/python -m src.validate_diagnostics \
  --output results/archive/diagnostic_observability/observations.json
```

The band patterns, fault effects, temperatures and repairs are constructed
benchmark conventions, not mechanistic biochemical predictions or physical
measurements. Source gels are requested individually and each charges the
configured $40 lane price; thermometer checks charge $20.
