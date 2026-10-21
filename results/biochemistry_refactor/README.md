# Biochemical checker refactor evidence

This change separates the acceptance model into configuration validation, trusted
sequence loading, junction/product checks, reagent metadata checks, per-well
composition, DNA amounts/ratios, and final-state incubation. Names state their
units and each check names its observation, expectation and basis. The entry
point orchestrates these steps instead of containing all calculations.

## Behavioral equivalence

`source_before.py` is an archival copy of the checker before this refactor, kept
only to reproduce the comparison. The runnable checker is `src/biochemistry.py`.
`check_equivalence.py` compares entire report dictionaries from both versions,
including check ordering, floating-point values, explanatory text, partial
reports, and configuration error messages.

Run from the worktree root:

```sh
.venv/bin/python results/biochemistry_refactor/check_equivalence.py
```

All **99 cases match exactly**, as recorded in `equivalence.json`, which also
records source/input hashes, command, environment and configuration. Inputs are
saved actual Kimi K3 rollout evidence from
`results/biochemistry/final_model_replay/evidence.json` plus explicitly
constructed counterexamples. These cover absent/invalid profiles, malformed
bounds and metadata, wrong DNA quantities, missing reagents, invalid volumes,
incubation boundaries, stale/unmixed evidence, cumulative exposure, incorrect
product sequences, ambiguous overlaps and duplicate FASTA IDs. Temporary
sequence mutations never overwrite the repository's sequence inputs.

This comparison makes no model calls and executes no generated protocol code.
It reuses saved observations from a real rollout; it is not a new agent rollout
or an experimental validation of biochemical success.

## Existing tests

Executed commands:

```sh
# Before and after the main refactor, with separate output files:
.venv/bin/python -m pytest -q tests/test_biochemistry.py \
  tests/test_biochemistry_ordering.py \
  --junitxml=results/biochemistry_refactor/before_tests.xml
.venv/bin/python -m pytest -q tests/test_biochemistry.py \
  tests/test_biochemistry_ordering.py \
  --junitxml=results/biochemistry_refactor/after_tests.xml

# Biochemical checks on the final source:
.venv/bin/python -m pytest -q tests/test_biochemistry.py \
  --junitxml=results/biochemistry_refactor/biochemistry_tests.xml

# Broader integration check:
.venv/bin/python -m pytest -q tests \
  --junitxml=results/biochemistry_refactor/full_tests.xml
```

The biochemical test file passes **24/24** on the final source. Targeted combined
outcomes match before and after: **25 passed, 9 failed, 1 setup error**. The
ordering failures already existed before this edit: the sequence-partition
loader requires 1000 bp partitions, but the current sequence files have different
lengths. They arise in `src/fragments.py` before the biochemical checker is
reached. Sequence data and ordering behavior were left untouched by this refactor.
The full suite reports **113 passed, 32 failed, and 1 setup error**; all 33
failed/setup-error tracebacks contain the same partition-length mismatch.
The full-suite outcome and unchanged targeted test outcomes are recorded in
`validation.json`; raw pytest output and JUnit XML are preserved here.

No acceptance thresholds, equations, scoring gates, report fields or scientific
claims were intentionally changed. The existing `configuration.valid` gate is
preserved for malformed profiles and simulation evidence. Dependencies did not
change. Broader schema validation or changes to scientific assumptions would be
separate changes.
