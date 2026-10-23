"""Real SDK integration checks using constructed protocols, not model rollouts."""
import asyncio
from pathlib import Path
import pytest
from src.runner import validate_code

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (ROOT / "examples/two_reagent_mix.py").read_text()
HEADER = REFERENCE.split('    for name in')[0]


def check(code, scenario="two_reagent_mix"):
    return asyncio.run(validate_code(code, scenario))


def test_reference_and_native_commands():
    result = check(REFERENCE)
    assert result["passed"], result["errors"]
    assert result["tips_used"] == 4
    assert result["final_wells"]["3:A1"] == {"water": 15, "reagent_A": 5}
    assert any("Aspirating" in command for command in result["opentrons_commands"])


@pytest.mark.parametrize("body,error", [
    ('    pipette.aspirate(5, stock["A1"])\n', "No tip attached"),
    ('    pipette.pick_up_tip()\n    pipette.aspirate(21, stock["A1"])\n', "outside pipette range"),
    ('    pipette.pick_up_tip()\n    pipette.aspirate(0.5, stock["A1"])\n', "outside pipette range"),
    ('    pipette.pick_up_tip()\n    pipette.aspirate(15, stock["A1"])\n    pipette.aspirate(10, stock["A1"])\n', "exceeds pipette capacity"),
    ('    pipette.pick_up_tip()\n    pipette.dispense(5, plate["A1"])\n', "exceeds liquid held"),
    ('    pipette.transfer(100, stock["A1"], plate["A1"])\n', "Insufficient usable liquid"),
    ('    pipette.pick_up_tip()\n    pipette.aspirate(5, stock["A1"])\n    pipette.dispense(5, plate["A1"])\n    pipette.aspirate(5, stock["A2"])\n', "carryover"),
    ('    for i in range(7):\n        pipette.pick_up_tip()\n        pipette.drop_tip()\n', "Tip budget"),
    ('    pipette.pick_up_tip(tips["A1"])\n    pipette.drop_tip()\n    pipette.pick_up_tip(tips["A1"])\n', "already been used"),
    ('    pipette.transfer(180, stock["A2"], plate["A1"])\n    pipette.transfer(20, stock["A1"], plate["A1"])\n    pipette.transfer(20, stock["A1"], plate["A1"])\n', "Well overflow"),
])
def test_physical_failures(body, error):
    result = check(HEADER + body)
    assert not result["passed"]
    assert error in " ".join(result["errors"])


def test_wrong_recipe_fails_even_with_valid_robot_commands():
    result = check(REFERENCE.replace('transfer(15,', 'transfer(14,'))
    assert not result["passed"]
    assert "water expected 15 uL, got 14" in " ".join(result["errors"])


def test_missing_mix():
    result = check(REFERENCE.replace(', mix_after=(3, 10)', ''))
    assert not result["passed"]
    assert "not been mixed" in " ".join(result["errors"])


def test_early_mix_does_not_count_after_addition():
    code = REFERENCE.replace('transfer(15, stock["A2"], plate[name])', 'transfer(15, stock["A2"], plate[name], mix_after=(3, 10))').replace('transfer(5, stock["A1"], plate[name], mix_after=(3, 10))', 'transfer(5, stock["A1"], plate[name])')
    result = check(code)
    assert not result["passed"]
    assert "not been mixed" in " ".join(result["errors"])


def test_saved_scenarios_are_independent():
    first = check(REFERENCE)
    second = check(REFERENCE)
    assert first["passed"] and second["passed"]
    assert first["final_wells"] == second["final_wells"]
    assert first["tips_used"] == second["tips_used"]


def test_panel_reference():
    code = (ROOT / "examples/three_reagent_panel.py").read_text()
    result = check(code, "three_reagent_panel")
    assert result["passed"], result["errors"]


def test_serial_dilution_tracks_mixture_components():
    code = (ROOT / "examples/serial_dilution.py").read_text()
    result = check(code, "serial_dilution")
    assert result["passed"], result["errors"]
    assert result["final_wells"]["3:A3"] == {"reagent_A": 2.5, "water": 17.5}
    assert sum(result["final_wells"]["3:A12"].values()) == 20
    bad = check(code.replace('    pipette.mix(3, 10, plate["A1"])\n', ''), "serial_dilution")
    assert not bad["passed"]
    assert "before sampling" in " ".join(bad["errors"])
