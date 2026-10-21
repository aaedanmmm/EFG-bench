from opentrons import protocol_api

metadata = {
    "protocolName": "sequence_recovery_02_gibson_7piece",
    "author": "benchmark",
    "description": (
        "Seven-piece Gibson assembly of fragment_001..fragment_006 plus the "
        "backbone source remainder into the circular 12484 bp benchmark target. "
        "20 uL reaction: 1 uL of each of the seven DNA stocks, 10 uL 2X Gibson "
        "master mix, 3 uL water; mixed 3 x 10 uL; incubated at 50 C for 60 min."
    ),
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # --- Labware ---------------------------------------------------------
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_module = protocol.load_module("temperature module gen2", 4)
    reaction_plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    # --- Pipette ---------------------------------------------------------
    p20 = protocol.load_instrument(
        "p20_single_gen2", mount="left", tip_racks=[tiprack]
    )

    # --- Source wells ----------------------------------------------------
    # 1:A1..1:A6 = fragment_001..fragment_006, 1:B1 = backbone,
    # 1:B2 = gibson_master_mix (2X), 1:B3 = water.
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    master_mix = tuberack["B2"]
    water = tuberack["B3"]

    dest = reaction_plate["A1"]

    # --- Reaction assembly (20 uL total) ---------------------------------
    # 1 uL of each of the seven DNA pieces (0.03 pmol each by construction).
    # Fresh tip for every stock to avoid any cross-contamination.
    for well_name in dna_wells:
        p20.transfer(1, tuberack[well_name], dest, new_tip="always")

    # 10 uL of 2X Gibson master mix -> 1X final in the 20 uL reaction.
    p20.transfer(10, master_mix, dest, new_tip="always")

    # 3 uL water to reach 20 uL, then mix the complete reaction 3 x 10 uL
    # immediately after this final liquid addition.
    p20.transfer(3, water, dest, mix_after=(3, 10), new_tip="always")

    # --- Incubation ------------------------------------------------------
    # Heating follows the final additions and mixing: 50 C for 60 minutes.
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
