"""Public-feedback scripted controls, not model rollouts or wet-lab evidence."""
import argparse
import json
from pathlib import Path

from src.design_lab import apply_action, grade_lab, new_lab
from src.design_recovery import load_recovery_scenarios


def run_control(scenario):
    lab, transcript = new_lab(), []

    def act(kind, **arguments):
        nonlocal lab
        lab, response = apply_action(scenario, lab, kind, **arguments)
        transcript.append({"kind": kind, "arguments": arguments, "response": response})
        return response

    # Constructed reference design, not an answer supplied to the agent.
    target = scenario["target_sequence"]
    sequences = [target[:500], target[460:960], target[920:]]
    stocks = [act("order_fragment", sequence=sequence)["fragment_id"] for sequence in sequences]
    polymerase = "taq_polymerase"
    act("order_reagent", item_id=polymerase)
    first = act("run_assembly", fragment_ids=stocks, polymerase=polymerase)["experiment_id"]
    act("measure_yield", experiment_id=first)
    act("select_product", experiment_id=first)
    before = grade_lab(scenario, lab["actions"])
    assert not before["passed"]

    # A verified-input control separates stock/design issues from shared equipment/enzyme issues.
    control = act("design_recovery_service", service="positive_control", polymerase=polymerase)
    if control["finding"] == "failed":
        temperature = act("design_recovery_service", service="thermometer_check")
        if temperature["measured_temperature_c"] != temperature["setpoint_c"]:
            act("design_recovery_service", service="calibrate_temperature")
        else:
            act("replace_design_reagent", item_id=polymerase)
    else:
        suspect = None
        for stock in stocks:
            reading = act("design_recovery_service", service="check_stock", fragment_id=stock)
            if not reading["bands_bp"]:
                suspect = stock
                break
        assert suspect is not None
        act("replace_design_stock", fragment_id=suspect)
    # Repair does not change an old reaction.
    assert not grade_lab(scenario, lab["actions"])["passed"]
    final = act("run_assembly", fragment_ids=stocks, polymerase=polymerase)["experiment_id"]
    act("measure_yield", experiment_id=final)
    act("select_product", experiment_id=final)
    result = grade_lab(scenario, lab["actions"])
    assert result["passed"], result
    return {"constructed": True, "scenario_id": scenario["id"], "before_repair": before,
            "after_repair": result, "actions": lab["actions"], "public_transcript": transcript}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    controls = [run_control(scenario) for scenario in load_recovery_scenarios(args.seed)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"constructed": True, "model": None,
        "note": "Scripted controls use real simulator actions and public diagnostic feedback. Not model rollouts.",
        "command": f"python -m src.validate_design_recovery --seed {args.seed} --output {args.output}",
        "seed": args.seed, "passed": all(item["after_repair"]["passed"] for item in controls),
        "controls": controls}, indent=2) + "\n")
    print(f"{len(controls)}/{len(controls)} constructed recovery controls passed: {args.output}")


if __name__ == "__main__":
    main()
