from opentrons import protocol_api

metadata = {
    "protocolName": "sequence_recovery_01 seven-piece Gibson assembly",
    "description": (
        "Assemble fragment_001..fragment_006 + backbone (1 uL each) with "
        "10 uL 2X Gibson master mix and 3 uL water (20 uL total); mix 3 x "
        "10 uL; incubate at 50 C for 60 min on the temperature module."
    ),
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware -------------------------------------------------------
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_module = protocol.load_module("temperature module gen2", 4)
    reaction_plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    pipette = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tiprack]
    )

    # Source wells -------------------------------------------------------
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]  # 6 fragments + backbone
    master_mix = tuberack["B2"]
    water = tuberack["B3"]
    dest = reaction_plate["A1"]

    # Build the 20 uL reaction ------------------------------------------
    # Water first, then the seven DNA pieces (1 uL each), master mix last.
    pipette.transfer(3, water, dest, new_tip="always")
    for well_name in dna_wells:
        pipette.transfer(1, tuberack[well_name], dest, new_tip="always")
    pipette.transfer(
        10, master_mix, dest, new_tip="always", mix_after=(3, 10)
    )

    # Incubate: heating follows the final additions and mixing ----------
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
