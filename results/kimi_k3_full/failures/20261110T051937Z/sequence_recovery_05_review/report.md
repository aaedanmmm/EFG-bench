# Biochemical review

Scenario: `sequence_recovery_05`. Evidence origin: actual Inspect rollout: openrouter/moonshotai/kimi-k3.

**Overall evaluation: PASS.**
Liquid handling: PASS. Biochemical acceptance model: `in_silico_conditions_satisfied`.

**Experimental outcome: NOT MEASURED.** This report checks declared reaction conditions and predicts sequence compatibility. It does not demonstrate actual assembly, yield, colonies, enzyme activity, expression, or biological function.

## Decision rules

Overall success requires valid liquid handling AND every applicable biochemical gate. No averaging can compensate for a failed gate. Inert mixing tasks have no biochemical score. Recommendations enforced as gates and benchmark assumptions are identified below.

## Expected versus observed

| Check | Result | Observed | Required | Basis |
| --- | --- | --- | --- | --- |
| input.linear_purified_dsdna | PASS | {"backbone": {"linear": true, "purified": true}, "fragment_001": {"linear": true, "purified": true}, "fragment_002": {"linear": true, "purified": true}, "fragment_003": {"linear": true, "purified": true}, "fragment_004": {"linear": true, "purified": true}, "fragment_005": {"linear": true, "purified": true}, "fragment_006": {"linear": true, "purified": true}} | "All specified DNA inputs are purified linear dsDNA" | supplied metadata; not a purity assay |
| junction.fragment_001->fragment_002.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.fragment_001.specificity | PASS | ["fragment_002+"] | ["fragment_002+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.fragment_002->fragment_003.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.fragment_002.specificity | PASS | ["fragment_003+"] | ["fragment_003+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.fragment_003->fragment_004.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.fragment_003.specificity | PASS | ["fragment_004+"] | ["fragment_004+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.fragment_004->fragment_005.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.fragment_004.specificity | PASS | ["fragment_005+"] | ["fragment_005+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.fragment_005->fragment_006.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.fragment_005.specificity | PASS | ["fragment_006+"] | ["fragment_006+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.fragment_006->backbone.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.fragment_006.specificity | PASS | ["backbone+"] | ["backbone+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| junction.backbone->fragment_001.homology | PASS | 30 | "Exact terminal overlap of 20..40 bp" | benchmark assumption |
| junction.backbone.specificity | PASS | ["fragment_001+"] | ["fragment_001+"] | conservative terminal-overlap uniqueness rule; includes self-joining and reverse orientations |
| product.sequence_identity | PASS | {"length_bp": 12484, "sha256": "57e23d1a07494e60968118ad7524152c67b61b21f7102ba92be5884575cad921"} | {"comparison": "Full circular sequence identity allowing rotation and whole-product reverse complement", "length_bp": 12484, "sha256": "57e23d1a07494e60968118ad7524152c67b61b21f7102ba92be5884575cad921"} | benchmark assumption |
| enzyme.active | PASS | true | true | supplied reagent metadata; not an enzyme activity measurement |
| 4:A1.reaction_volume | PASS | 20.0 | {"tolerance_ul": 0.01, "volume_ul": 20.0} | NEB 20 uL reference formulation, parameterized in benchmark |
| 4:A1.reagent_identity | PASS | [] | [] | closed reagent identity model; unmodeled additives fail |
| 4:A1.master_mix_concentration | PASS | 1.0 | {"range_x": [0.95, 1.05]} | NEB 2X stock diluted to 1X; tolerance is a benchmark assumption |
| 4:A1.dna_present.fragment_001 | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.fragment_002 | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.fragment_003 | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.fragment_004 | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.fragment_005 | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.fragment_006 | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.dna_present.backbone | PASS | 1.0 | ">0 uL" | benchmark assumption |
| 4:A1.vector_mass | PASS | 104.325 | {"range_ng": [100, 110]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.total_dna | PASS | 0.21 | {"formula": "mass_ng * 1000 / (length_bp * molecular_weight_per_bp)", "molecular_weight_g_mol_bp": 650.0, "range_pmol": [0.2, 0.5]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.molar_ratio.fragment_001 | PASS | 1.0 | {"insert_to_backbone_range": [0.95, 1.05]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.molar_ratio.fragment_002 | PASS | 1.0 | {"insert_to_backbone_range": [0.95, 1.05]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.molar_ratio.fragment_003 | PASS | 1.0 | {"insert_to_backbone_range": [0.95, 1.05]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.molar_ratio.fragment_004 | PASS | 1.0 | {"insert_to_backbone_range": [0.95, 1.05]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.molar_ratio.fragment_005 | PASS | 1.0 | {"insert_to_backbone_range": [0.95, 1.05]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.molar_ratio.fragment_006 | PASS | 1.0 | {"insert_to_backbone_range": [0.95, 1.05]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| 4:A1.incubation | PASS | {"all_events": "see incubation history and evidence.json", "qualified_seconds": 3600.0} | {"after_final_addition_and_mixing": true, "seconds": [3600, 3600], "temperature_c": [49, 51]} | Constructed seven-piece benchmark extrapolation; stock amounts, equimolar ratios, 49-51 C tolerance and 60 min duration are acceptance gates, not experimentally validated seven-piece guidance |
| execution.liquid_handling | PASS | true | true | independent virtual-robot and liquid-accounting checks |

## Reaction calculations

### 4:A1

Volume: 20 uL; master mix: 1X; total DNA: 0.21 pmol.

| DNA component | Volume (uL) | Stock (ng/uL) | Mass (ng) | Length (bp) | Amount (pmol) |
| --- | ---: | ---: | ---: | ---: | ---: |
| fragment_001 | 1 | 15.054 | 15.054 | 772 | 0.03 |
| fragment_002 | 1 | 30.537 | 30.537 | 1566 | 0.03 |
| fragment_003 | 1 | 22.1325 | 22.1325 | 1135 | 0.03 |
| fragment_004 | 1 | 12.636 | 12.636 | 648 | 0.03 |
| fragment_005 | 1 | 37.4985 | 37.4985 | 1923 | 0.03 |
| fragment_006 | 1 | 25.35 | 25.35 | 1300 | 0.03 |
| backbone | 1 | 104.325 | 104.325 | 5350 | 0.03 |

## Predicted product

Topology: circular. Junction order: fragment_001 → fragment_002 → fragment_003 → fragment_004 → fragment_005 → fragment_006 → backbone → fragment_001.

| Junction | Exact overlap (bp) | Overlap sequence |
| --- | ---: | --- |
| fragment_001 → fragment_002 | 30 | `GAAGGTGATTTCACCCGCTCCTTCCCCACC` |
| fragment_002 → fragment_003 | 30 | `CAAGCGCACAGAGCCGCGCAGCGAGGCAGA` |
| fragment_003 → fragment_004 | 30 | `GCCGGATCTGAAGCCTGGAGTGGGGTCCCG` |
| fragment_004 → fragment_005 | 30 | `AAGTGGCGCAGCTCACAGAGCTGGGGGCCA` |
| fragment_005 → fragment_006 | 30 | `TTGTCTTCGCAGAGGTGTAAGGACAAGTTG` |
| fragment_006 → backbone | 30 | `TGTGCGGCCCGGAGAGCTCCCGGCTGCAGG` |
| backbone → fragment_001 | 30 | `ACAAGCTCTCCAGGCTTGCTACCATTTAAA` |

[Predicted product FASTA](predicted_product.fasta): 12484 bp. Full sequence comparison allows circular rotation and whole-product reverse complement; it does not use size alone.

Trusted sequence input: `data/biochemistry/supplied_partitions_gibson.fasta`, SHA-256 `4aebeab7369b9974122cc98359747383ed4b85d4acd8744a658f9d7bc9227fd8`.

## Incubation history

Only time at the accepted temperature, after final liquid changes and mixing, contributes. Temperature setpoints alone contribute no time.

- `4:A1`: 50 C for 3600 seconds; mixed=True; liquid revision=9; composition={"backbone": 1.0, "fragment_001": 1.0, "fragment_002": 1.0, "fragment_003": 1.0, "fragment_004": 1.0, "fragment_005": 1.0, "fragment_006": 1.0, "gibson_master_mix": 10.0, "water": 3.0}.

## Assumptions and limits

- Seven prepared stocks each contain an exact data/sequences core plus a constructed 30 bp closing/adjacent overlap. Preparation is assumed, not performed by the OT-2.
- Equal 0.03 pmol per piece at 1 uL each is set by constructed stock concentrations. 20 uL reaction, 1X master mix, 50 C and 60 min are benchmark gates.
- Seven-piece acceptance criteria extrapolate beyond the cited NEB 4-6 piece formulation; no seven-piece efficiency or yield is claimed.
- The sequence called backbone is the original trailing genomic remainder, not a cloning vector. Circularity is a constructed target topology.
- No kinetic/yield or functional biological model. Heating must follow final additions/mixing.

## Sources

- [NEB E2611 manual: DNA mass-to-pmol calculation, total DNA, vector mass/insert ratios, 2X mix dilution and 50 C incubation.](https://nebuilderv1.neb.com/media/manualE2611.pdf)
- [NEB product protocol overview; appropriate terminal overlaps and 50 C incubation.](https://www.neb.com/en/products/e2611-gibson-assembly-master-mix)

## Full evidence

[Machine-readable evidence](evidence.json) contains every gate, numeric observation, liquid-handling error, thermal event, and SDK command. The DNA product is a conditional sequence prediction, even when another required gate fails.
