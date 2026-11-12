from opentrons import protocol_api

metadata = {
    "protocolName": "sequence_recovery_04 seven-piece Gibson assembly",
    "description": (
        "Assemble fragment_001..fragment_006 and backbone into the circular "
        "12484 bp benchmark product. 20 uL reaction: 1 uL of each of the seven "
        "DNA pieces, 10 uL 2X Gibson master mix (1X final), 3 uL water; mix "
        "3 x 10 uL; incubate at 50 C for 60 minutes."
    ),
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
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

    reaction = reaction_plate["A1"]

    # 1 uL of each of the seven DNA pieces (fresh tip per stock, no carryover)
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    for well_name in dna_wells:
        p20.transfer(1, tuberack[well_name], reaction, new_tip="always")

    # 10 uL 2X Gibson master mix -> 1X final in the 20 uL reaction
    p20.transfer(10, tuberack["B2"], reaction, new_tip="always")

    # 3 uL nuclease-free water to reach 20 uL total; mix 3 x 10 uL on this
    # final liquid addition
    p20.transfer(
        3, tuberack["B3"], reaction, mix_after=(3, 10), new_tip="always"
    )

    # Incubate at 50 C for 60 minutes AFTER final additions and mixing
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
