from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly (ambiguous_recovery_06)",
    "description": (
        "Assemble fragment_001..fragment_006 + backbone (1 uL each) with "
        "10 uL 2X Gibson master mix and 3 uL water (20 uL total), mix, "
        "incubate 50 C for 60 min on temperature module gen2."
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
    plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    # --- Pipette ---------------------------------------------------------
    pipette = protocol.load_instrument(
        "p20_single_gen2", mount="left", tip_racks=[tiprack]
    )

    dest = plate["A1"]

    # --- Sources ---------------------------------------------------------
    water = tuberack["B3"]
    master_mix = tuberack["B2"]
    # fragment_001..fragment_006 in A1..A6, backbone in B1
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]

    # --- Build the 20 uL reaction ---------------------------------------
    # Water first (fresh tip)
    pipette.transfer(3, water, dest, new_tip="always")

    # 1 uL of each of the seven DNA pieces (fresh tip each)
    for well in dna_wells:
        pipette.transfer(1, tuberack[well], dest, new_tip="always")

    # 2X master mix last; mix the complete reaction 3 x 10 uL
    pipette.transfer(
        10, master_mix, dest, new_tip="always", mix_after=(3, 10)
    )

    # --- Incubation: heating follows final additions/mixing -------------
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
