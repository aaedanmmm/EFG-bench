from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly (ambiguous_recovery_02)",
    "author": "benchmark",
    "description": (
        "Assemble fragment_001..fragment_006 + backbone (1 uL each) with "
        "10 uL 2X Gibson master mix and 3 uL water in 4:A1 (20 uL total), "
        "mix 3 x 10 uL, then incubate at 50 C for 60 minutes."
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
    pipette = protocol.load_instrument(
        "p20_single_gen2", mount="left", tip_racks=[tiprack]
    )

    dest = reaction_plate["A1"]

    # DNA pieces: 1 uL each of fragment_001..fragment_006 and backbone.
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    for well in dna_wells:
        pipette.transfer(1, tuberack[well], dest, new_tip="always")

    # 10 uL 2X Gibson master mix (1X final in 20 uL).
    pipette.transfer(10, tuberack["B2"], dest, new_tip="always")

    # 3 uL water, then mix 3 x 10 uL immediately after the final addition.
    pipette.transfer(
        3, tuberack["B3"], dest, new_tip="always", mix_after=(3, 10)
    )

    # Incubate: heating follows the final additions and mixing.
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
