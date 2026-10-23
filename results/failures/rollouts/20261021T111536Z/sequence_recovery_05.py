from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly into circular benchmark target",
    "author": "benchmark",
    "description": (
        "Combine fragment_001..fragment_006 and backbone (1 uL each) with "
        "2X Gibson master mix (10 uL) and water (3 uL) in 4:A1, mix 3x10 uL, "
        "then incubate at 50 C for 60 minutes."
    ),
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_module = protocol.load_module("temperature module gen2", 4)
    reaction_plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    # Pipette
    p20 = protocol.load_instrument(
        "p20_single_gen2", mount="left", tip_racks=[tiprack]
    )

    # Source wells
    fragment_wells = {
        "fragment_001": tuberack["A1"],
        "fragment_002": tuberack["A2"],
        "fragment_003": tuberack["A3"],
        "fragment_004": tuberack["A4"],
        "fragment_005": tuberack["A5"],
        "fragment_006": tuberack["A6"],
        "backbone": tuberack["B1"],
    }
    master_mix_well = tuberack["B2"]
    water_well = tuberack["B3"]

    dest = reaction_plate["A1"]

    # Add 1 uL of each DNA piece (fresh tip per stock to avoid carryover)
    for name in [
        "fragment_001",
        "fragment_002",
        "fragment_003",
        "fragment_004",
        "fragment_005",
        "fragment_006",
        "backbone",
    ]:
        p20.transfer(1, fragment_wells[name], dest, new_tip="always")

    # Add 10 uL 2X Gibson master mix (final 1X in 20 uL)
    p20.transfer(10, master_mix_well, dest, new_tip="always")

    # Add 3 uL water to reach 20 uL total, then mix 3 x 10 uL
    p20.transfer(3, water_well, dest, new_tip="always", mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes after final additions and mixing
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
