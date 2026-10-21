# Biochemical review

Scenario: `gibson_assembly`. Evidence origin: replay of actual Kimi K3 submission from Inspect rollout 20261021T071800Z.

**Overall evaluation: PASS.**
Liquid handling: PASS. Biochemical acceptance model: `in_silico_conditions_satisfied`.

**Experimental outcome: NOT MEASURED.** This report checks declared reaction conditions and predicts sequence compatibility. It does not demonstrate actual assembly, yield, colonies, enzyme activity, expression, or biological function.

## Decision rules

Overall success requires valid liquid handling AND every applicable biochemical gate. No averaging can compensate for a failed gate. Inert mixing tasks have no biochemical score. Recommendations enforced as gates and benchmark assumptions are identified below.

## Expected versus observed

| Check | Result | Observed | Required | Basis |
| --- | --- | --- | --- | --- |
| input.linear_purified_dsdna | PASS | {"backbone": {"linear": true, "purified": true}, "insert_A": {"linear": true, "purified": true}, "insert_B": {"linear": true, "purified": true}} | "All specified DNA inputs are purified linear dsDNA" | supplied metadata; not a purity assay |
| junction.backbone->insert_A.homology | PASS | 20 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.backbone.specificity | PASS | ["insert_A+"] | ["insert_A+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.insert_A->insert_B.homology | PASS | 20 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.insert_A.specificity | PASS | ["insert_B+"] | ["insert_B+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.insert_B->backbone.homology | PASS | 20 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.insert_B.specificity | PASS | ["backbone+"] | ["backbone+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| product.sequence_identity | PASS | {"length_bp": 2340, "sha256": "3ad8ae387d43b2cc0099aa9843f78ec60c1c16cf6033d39a61d9c9d7efc791fa"} | {"comparison": "Full circular sequence identity allowing rotation and whole-product reverse complement", "length_bp": 2340, "sha256": "3ad8ae387d43b2cc0099aa9843f78ec60c1c16cf6033d39a61d9c9d7efc791fa"} | benchmark assumption |
| enzyme.active | PASS | true | true | supplied reagent metadata; not an enzyme activity measurement |
| 4:A1.reaction_volume | PASS | 20.0 | {"tolerance_ul": 0.01, "volume_ul": 20.0} | NEB 20 uL reference formulation, parameterized in benchmark |
| 4:A1.reagent_identity | PASS | [] | [] | closed reagent identity model; unmodeled additives fail |
| 4:A1.master_mix_concentration | PASS | 1.0 | {"range_x": [0.95, 1.05]} | NEB 2X stock diluted to 1X; tolerance is a benchmark assumption |
| 4:A1.dna_present.backbone | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.insert_A | PASS | 2.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.insert_B | PASS | 2.0 | ">0 uL" | benchmark assumption |
| 4:A1.vector_mass | PASS | 50.0 | {"range_ng": [50, 100]} | NEB recommended vector mass; enforced here as an acceptance gate |
| 4:A1.total_dna | PASS | 0.38461538461538464 | {"formula": "mass_ng * 1000 / (length_bp * molecular_weight_per_bp)", "molecular_weight_g_mol_bp": 650.0, "range_pmol": [0.02, 0.5]} | NEB E2611 DNA-input guidance; dsDNA approximation |
| 4:A1.molar_ratio.insert_A | PASS | 2.0 | {"insert_to_backbone_range": [2, 3]} | NEB recommended insert excess; enforced here as an acceptance gate |
| 4:A1.molar_ratio.insert_B | PASS | 2.0 | {"insert_to_backbone_range": [2, 3]} | NEB recommended insert excess; enforced here as an acceptance gate |
| 4:A1.incubation | PASS | {"all_events": "see incubation history and evidence.json", "qualified_seconds": 3600.0} | {"after_final_addition_and_mixing": true, "seconds": [900, 3600], "temperature_c": [49, 51]} | NEB 50 C and 15-60 min for 2-3 fragments; temperature tolerance and final-state requirement are benchmark assumptions |
| execution.liquid_handling | PASS | true | true | independent virtual-robot and liquid-accounting checks |

## Reaction calculations

### 4:A1

Volume: 20 uL; master mix: 1X; total DNA: 0.384615 pmol.

| DNA component | Volume (uL) | Stock (ng/uL) | Mass (ng) | Length (bp) | Amount (pmol) |
| --- | ---: | ---: | ---: | ---: | ---: |
| backbone | 1 | 50 | 50 | 1000 | 0.0769231 |
| insert_A | 2 | 30 | 60 | 600 | 0.153846 |
| insert_B | 2 | 40 | 80 | 800 | 0.153846 |

## Predicted product

Topology: circular. Junction order: backbone → insert_A → insert_B → backbone.

| Junction | Exact overlap (bp) | Overlap sequence |
| --- | ---: | --- |
| backbone → insert_A | 20 | `TCTCTCGCCAGGCCAGTCTT` |
| insert_A → insert_B | 20 | `GCTTTGCTAAACATACTTGC` |
| insert_B → backbone | 20 | `TGGTGTATTGCCTTGTTACT` |

[Predicted product FASTA](predicted_product.fasta): 2340 bp. Full sequence comparison allows circular rotation and whole-product reverse complement; it does not use size alone.

Trusted sequence input: `data/biochemistry/synthetic_gibson.fasta`, SHA-256 `89ed69fe4c8b43d58cec356163ab120ad35a048c4bfd16a3d67ba36c2569f6a4`.

## Incubation history

Only time at the accepted temperature, after final liquid changes and mixing, contributes. Temperature setpoints alone contribute no time.

- `4:A1`: 50 C for 3600 seconds; mixed=True; liquid revision=5; composition={"backbone": 1.0, "gibson_master_mix": 10.0, "insert_A": 2.0, "insert_B": 2.0, "water": 5.0}.

## Assumptions and limits

- Exact unique terminal homology of 20-40 bp; no mismatches tolerated. This is a conservative benchmark rule, not a universal Gibson success boundary.
- 49-51 C is a benchmark tolerance around the published 50 C setpoint, not a validated activity curve.
- All input fragments are purified linear dsDNA with the stated concentrations. Enzyme active/inactive labels are supplied metadata, not measured activity.
- No kinetic/yield model; circular sequence identity does not establish transformation, expression, or biological function.
- Heating must occur after the final liquid change and final mixing; post-incubation transfers require a new qualifying incubation.

## Sources

- [NEB E2611 manual: DNA mass-to-pmol calculation, total DNA, vector mass/insert ratios, 2X mix dilution and 50 C incubation.](https://nebuilderv1.neb.com/media/manualE2611.pdf)
- [NEB product protocol overview; appropriate terminal overlaps and 50 C incubation.](https://www.neb.com/en/products/e2611-gibson-assembly-master-mix)

## Full evidence

[Machine-readable evidence](evidence.json) contains every gate, numeric observation, liquid-handling error, thermal event, and SDK command. The DNA product is a conditional sequence prediction, even when another required gate fails.
