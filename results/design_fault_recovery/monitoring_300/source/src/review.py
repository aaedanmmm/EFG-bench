"""Generate an auditable biochemical review from fresh simulation evidence."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from src.runner import validate_code


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("|", "\\|").replace("\n", " ")


def write_review(validation, directory, *, origin="unclassified artifact"):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "evidence.json").write_text(json.dumps(validation, indent=2) + "\n")
    bio = validation.get("biochemistry", {})
    checks = bio.get("checks", [])
    lines = [
        "# Biochemical review", "",
        f"Scenario: `{validation.get('scenario_id', 'unknown')}`. Evidence origin: {origin}.", "",
        f"**Overall evaluation: {'PASS' if validation.get('passed') else 'FAIL'}.**",
        f"Liquid handling: {'PASS' if validation.get('liquid_handling_passed') else 'FAIL'}. "
        f"Biochemical acceptance model: `{bio.get('status', 'not_evaluated')}`.", "",
        "**Experimental outcome: NOT MEASURED.** This report checks declared reaction conditions and predicts sequence compatibility. It does not demonstrate actual assembly, yield, colonies, enzyme activity, expression, or biological function.", "",
        "## Decision rules", "",
        "Overall success requires valid liquid handling AND every applicable biochemical gate. No averaging can compensate for a failed gate. Inert mixing tasks have no biochemical score. Recommendations enforced as gates and benchmark assumptions are identified below.", "",
        "## Expected versus observed", "",
        "| Check | Result | Observed | Required | Basis |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in checks:
        # Keep potentially lengthy time-series evidence out of the table, but retain
        # every full observation in evidence.json and the incubation section below.
        observed = item["observed"]
        if isinstance(observed, dict) and "all_incubation_events" in observed:
            observed = {"qualified_seconds": observed["qualified_seconds"], "all_events": "see incubation history and evidence.json"}
        lines.append(f"| {item['id']} | {'PASS' if item['passed'] else 'FAIL'} | {compact(observed)} | {compact(item['expected'])} | {item['basis']} |")
    if not checks:
        lines.extend(["", "No biochemical model is configured for this task; biochemical success is not scored."])
    lines.extend(["", "## Reaction calculations", ""])
    for reaction in bio.get("reactions", []):
        lines.extend([f"### {reaction['well']}", "", f"Volume: {reaction['volume_ul']:g} uL; master mix: {reaction['master_mix_final_x']:g}X; total DNA: {reaction['total_dna_pmol']:.6g} pmol.", "", "| DNA component | Volume (uL) | Stock (ng/uL) | Mass (ng) | Length (bp) | Amount (pmol) |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for name, quantity in reaction["dna"].items():
            lines.append(f"| {name} | {quantity['volume_ul']:g} | {quantity['concentration_ng_ul']:g} | {quantity['mass_ng']:g} | {quantity['length_bp']} | {quantity['pmol']:.6g} |")
    assembly = bio.get("assembly")
    if assembly:
        lines.extend(["", "## Predicted product", "", "Topology: circular. Junction order: " + " → ".join(assembly["order"]) + " → " + assembly["order"][0] + ".", "", "| Junction | Exact overlap (bp) | Overlap sequence |", "| --- | ---: | --- |"])
        for junction in assembly["junctions"]:
            lines.append(f"| {junction['left']} → {junction['right']} | {junction['overlap_bp']} | `{junction['overlap_sequence']}` |")
        if assembly["predicted_sequence"]:
            sequence = assembly["predicted_sequence"]
            (directory / "predicted_product.fasta").write_text(">predicted_product IN_SILICO_ONLY; not an observed molecule\n" + "\n".join(sequence[i:i+80] for i in range(0, len(sequence), 80)) + "\n")
            lines.extend(["", f"[Predicted product FASTA](predicted_product.fasta): {len(sequence)} bp. Full sequence comparison allows circular rotation and whole-product reverse complement; it does not use size alone."])
        lines.extend(["", f"Trusted sequence input: `{assembly['sequence_file']}`, SHA-256 `{assembly['sequence_file_sha256']}`."])
    lines.extend(["", "## Incubation history", "", "Only time at the accepted temperature, after final liquid changes and mixing, contributes. Temperature setpoints alone contribute no time.", ""])
    for event in validation.get("events", []):
        if event["action"] == "incubate":
            lines.append(f"- `{event['well']}`: {event['temperature_c']:g} C for {event['seconds']:g} seconds; mixed={event['mixed']}; liquid revision={event['revision']}; composition={compact(event['components_ul'])}.")
    lines.extend(["", "## Assumptions and limits", ""])
    lines.extend("- " + item for item in bio.get("assumptions", []))
    lines.extend(["", "## Sources", ""])
    lines.extend(f"- [{item['description']}]({item['url']})" for item in bio.get("references", []))
    lines.extend(["", "## Full evidence", "", "[Machine-readable evidence](evidence.json) contains every gate, numeric observation, liquid-handling error, thermal event, and SDK command. The DNA product is a conditional sequence prediction, even when another required gate fails.", ""])
    (directory / "report.md").write_text("\n".join(lines))
    return directory / "report.md"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--scenario", default="sequence_assembly")
    parser.add_argument("--output", type=Path, default=Path("results/biochemistry_review"))
    parser.add_argument("--origin", default="user-supplied protocol; no provenance independently verified")
    args = parser.parse_args()
    source = args.protocol.read_text()
    report = await validate_code(source, args.scenario)
    report["protocol_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    report["review_command"] = ["python", "-m", "src.review", str(args.protocol), "--scenario", args.scenario, "--output", str(args.output), "--origin", args.origin]
    path = write_review(report, args.output, origin=args.origin)
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
