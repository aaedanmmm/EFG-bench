# Reviewing biochemical scoring

Current active tasks use **seven data/sequences-derived DNA pieces**, with a 12,484 bp target. See the [current design and configuration](supplied_sequence_assembly.md). Three-piece sizes/examples below describe archived regression profiles.

Start with the [actual Kimi K3 biochemical review](../results/archive/rollouts/20261021T071800Z/gibson_assembly_review/report.md).
It includes expected and observed values for every gate, DNA amounts in ng and
pmol, insert:backbone ratios, exact junction overlaps, the predicted product FASTA,
incubation events, assumptions, references, and the full JSON evidence.

Compare it with the [constructed failing control](../results/archive/biochemistry/no_incubation_review/report.md):
all liquid-handling checks pass, but incubation is missing, so the overall score
is zero. This control is deliberately constructed, not a model rollout or an
experimental result.

## Reading the checker

`src/biochemistry.py` follows the evaluation in the same order as the report.
Start at `evaluate_biochemistry()` for orchestration; `evaluate_reaction()` shows
what happens for each well. The individual steps are:

| Question | Function |
| --- | --- |
| Is the profile supported and are its numerical bounds valid? | `validate_criteria` |
| Which DNA records and orientations are being assembled? | `load_assembly_inputs` and `AssemblyInputs` |
| Are the declared inputs linear and purified? | `check_input_metadata` |
| Does each junction have a unique compatible terminal partner? | `check_junctions` and `terminal_partners` |
| Does the predicted complete circular sequence match the target? | `assemble_circular_product` and `check_product_identity` |
| Is the supplied master mix declared active? | `check_master_mix_metadata` |
| Are the well volume, reagent identities and master-mix dilution correct? | `check_reaction_composition` |
| How much DNA is present, and are its amounts and ratios acceptable? | `calculate_dna_quantities` and `check_dna_amounts` |
| Was the final mixed reaction incubated for sufficient time? | `check_incubation` |

Variable names carry units: `volume_ul`, `mass_ng`, `length_bp`, `amount_pmol`,
`temperature_c`, and `qualified_seconds`. DNA amount is calculated explicitly as
`mass_ng * 1000 / (length_bp * molecular_weight_per_bp)`. Incubation counts only
when temperature, mixing, final liquid revision, and component volumes all match.

`add_check()` writes the shared evidence schema. Each call names `observed`,
`expected`, and `basis` explicitly so the rule can be read independently of its
report formatting. The refactor preserves the existing public report, check
order, acceptance thresholds, and `configuration.valid` failure gate for malformed
profiles or evidence. Its comparison evidence is in
[results/archive/biochemistry_refactor/](../results/archive/biochemistry_refactor/README.md).

## What the score means

The Inspect scorer independently reruns the saved protocol. For a biochemical
task, success requires BOTH successful liquid handling and every biochemical gate.
The JSON `score_breakdown` reports `overall`, `liquid_handling`, and `biochemistry`
separately. Cost and tip efficiency are gated on overall correctness. A missing
biochemistry specification yields `not_applicable`, not biochemical success.
An unsupported or malformed biochemical profile fails closed.

The current `gibson_v1` model checks:

1. Supplied DNA identities, linear/purified metadata, and presence of every fragment.
2. Exact terminal overlaps for every junction, including circular closure;
   competing terminal partners, self-joining, and reverse orientations are rejected.
3. The entire predicted circular product sequence against the trusted target;
   matching size alone is insufficient. Circular rotations and whole-product
   reverse complements count as the same molecule.
4. Reaction volume, closed reagent identity, master-mix dilution, and supplied
   enzyme active/inactive metadata.
5. DNA mass and molarity from fragment length and stock concentration, vector
   mass, total DNA amount, and insert:backbone molar ratios.
6. Real temperature-module calls and time at the configured setpoint range,
   after additions and mixing. Setting temperature or writing a comment alone
   supplies no incubation time. Liquid revisions prevent heating an earlier
   mixture from qualifying a later mixture. Qualifying exposure is accumulated.

The initial profile uses the NEB E2611 reference formulation and input guidance.
The configured ranges, conservative overlap-uniqueness rule, and temperature
measurement tolerance are **benchmark acceptance criteria**, not universal
boundaries between biochemical success and failure. Each report labels its basis.

The model assumes ideal homogeneous liquids and the stated concentrations. It
uses a configurable dsDNA mass approximation (650 g/mol/bp in this profile), not
a measured molecular weight. Fragment purity and enzyme activity are supplied
metadata. It does not infer them from a successful pipetting run.

**The experimental result remains `not_measured`.** Passing necessary in-silico
conditions does not demonstrate DNA assembly yield, transformation, colonies,
sequence of an observed sample, expression, or biological function. No assay
results were supplied. The predicted FASTA is labeled as a prediction. Secondary
structure, detailed reaction kinetics, evaporation, sequence-dependent enzyme
performance, contaminant chemistry, and calibrated success probabilities are not
modeled.

## Run and review

```sh
.venv/bin/python -m src.run_eval --suite biochemistry --message-limit 40 \
  --env-file ../MATS-work-test/.env --model openrouter/moonshotai/kimi-k3
```

Every biochemical rollout automatically exports `<sample>_review/report.md`,
`evidence.json`, and `predicted_product.fasta` beside the Inspect log and submitted
Python protocol. For a fresh review of any supported saved protocol:

```sh
.venv/bin/python -m src.review examples/gibson_assembly.py \
  --scenario gibson_assembly --output results/my_biochemical_review \
  --origin 'constructed reference'
```

This command uses the bounded runtime; it does not execute arbitrary Python.
It exits 0 on overall pass and 1 on fail, making it suitable for automated checks.
Read the report alongside the [task profile](../data/biochemistry_tasks.json) and
[checker implementation](../src/biochemistry.py).

## Change the criteria or use your own sequences

Edit or add a scenario in `data/biochemistry_tasks.json`. Define a sequence FASTA
inside the repository containing uniquely named input fragments and a separate
expected product, then reference their IDs in `biochemistry.dna` and
`expected_product_id`. Set measured stock concentrations, supplied purity and
activity metadata, declared orientations and assembly order, reaction wells, and
explicit numerical criteria. Update the expected liquid targets and source
inventory consistently. The checker reads trusted scenario files; model prose
and code cannot redefine the intended sequence or thresholds.

The included sequences are deterministic random, synthetic test fixtures with
no assigned biological function. This synthetic profile does not silently treat
other sequence partitions as assembly-ready: real fragments require compatible
terminal homology, an explicit linearized-vector design, and a trusted expected
product. Add tests for each new reaction model before enabling it for scoring.

## Verification and evidence

`tests/test_biochemistry.py` covers correct formulae and sequence identity,
incorrect concentration/ratio, inactive enzyme metadata, missing fragments,
wrong same-length products, reversed fragments, ambiguous ends, invalid profiles,
short/missing/wrong-temperature incubation, heating before final additions,
stale evidence, scorer gating, and report contents. Perturbed evidence fixtures
are explicitly labeled constructed counterexamples. Integration tests call real
Opentrons virtual hardware. Run with:

```sh
.venv/bin/python -m pytest -q tests --junitxml=results/local_checks/biochemistry_tests.xml
```

The actual rollout, test output, source hashes, final replay and credential-scan
outcome are indexed in [results/archive/biochemistry/README.md](../results/archive/biochemistry/README.md).
