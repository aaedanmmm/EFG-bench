metadata = {
    "protocolName": "Seven-piece Gibson assembly (sequence_recovery_04)",
    "apiLevel": "2.19"
}


def run(protocol):
    # Deck layout: slot 1 source tube rack, slot 2 tip rack,
    # slot 4 temperature module with the reaction plate.
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    pip = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])

    rxn = plate["A1"]

    # Add 1 uL of each of the seven DNA pieces
    for well in ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]:
        pip.transfer(1.0, rack[well], rxn, new_tip="always")

    # Add 10 uL 2X Gibson master mix
    pip.transfer(10.0, rack["B2"], rxn, new_tip="always")

    # Add 3 uL water (final addition), then mix 3 x 10 uL
    pip.transfer(3.0, rack["B3"], rxn, new_tip="always", mix_after=(3, 10.0))

    # Incubate 50 C for 60 minutes after final additions and mixing
    temp_mod.set_temperature(50.0)
    protocol.delay(minutes=60)
    temp_mod.deactivate()
