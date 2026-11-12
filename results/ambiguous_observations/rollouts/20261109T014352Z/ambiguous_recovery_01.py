from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly (constructed benchmark)",
    "author": "benchmark",
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)

    # Temperature module gen2 in slot 4 with the aluminum-block plate
    temp_module = protocol.load_module("temperature module gen2", 4)
    reaction_plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    pipette = protocol.load_instrument(
        "p20_single_gen2", mount="left", tip_racks=[tiprack]
    )

    reaction = reaction_plate["A1"]

    # Bring the block to the 50 C incubation temperature
    temp_module.set_temperature(50)

    # Add 1 uL of each of the seven DNA pieces (fresh tip for each stock)
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    for well in dna_wells:
        pipette.transfer(1, tuberack[well], reaction, new_tip="always")

    # 10 uL of 2X Gibson master mix (1X final in 20 uL)
    pipette.transfer(10, tuberack["B2"], reaction, new_tip="always")

    # 3 uL water to reach 20 uL total; mix 3 x 10 uL after the final addition
    pipette.transfer(
        3, tuberack["B3"], reaction, new_tip="always", mix_after=(3, 10)
    )

    # Incubate 60 minutes at 50 C, then release the module
    protocol.delay(minutes=60)
    temp_module.deactivate()
