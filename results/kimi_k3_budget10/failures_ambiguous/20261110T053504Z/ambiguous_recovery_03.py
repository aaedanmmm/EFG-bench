from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly (ambiguous_recovery_03)",
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", "1"
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    temp_mod = protocol.load_module("temperature module gen2", "4")
    plate = temp_mod.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    pipette = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tiprack]
    )

    dest = plate["A1"]

    # Seven DNA pieces: 1 uL each (fragment_001..006 in A1..A6, backbone in B1)
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    for well in dna_wells:
        pipette.transfer(1, tuberack[well], dest, new_tip="always")

    # Water: 3 uL
    pipette.transfer(3, tuberack["B3"], dest, new_tip="always")

    # 2X Gibson master mix last: 10 uL (1X final in 20 uL), then mix 3 x 10 uL
    pipette.transfer(
        10, tuberack["B2"], dest, new_tip="always", mix_after=(3, 10)
    )

    # Incubate at 50 C for exactly 60 minutes (3600 s);
    # heating follows the final additions and mixing.
    temp_mod.set_temperature(50)
    protocol.delay(minutes=60)
    temp_mod.deactivate()
