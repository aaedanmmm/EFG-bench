from opentrons import protocol_api

metadata = {
    "protocolName": "sequence_recovery_01 seven-piece Gibson assembly",
    "description": (
        "Assemble fragment_001..fragment_006 and backbone (7 overlap-ready "
        "pieces) into the circular benchmark target in 4:A1; 20 uL reaction, "
        "1X Gibson master mix, 50 C for 60 min."
    ),
    "apiLevel": "2.19",
}


def run(ctx: protocol_api.ProtocolContext):
    # --- Labware ---
    tube_rack = ctx.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", "1"
    )
    tip_rack = ctx.load_labware("opentrons_96_tiprack_20ul", "2")
    temp_module = ctx.load_module("temperature module gen2", "4")
    reaction_plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    # --- Pipette ---
    p20 = ctx.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tip_rack]
    )

    # --- Wells ---
    dest = reaction_plate["A1"]
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]  # 7 DNA pieces
    master_mix_well = tube_rack["B2"]
    water_well = tube_rack["B3"]

    # --- Build the 20 uL reaction ---
    # 1 uL of each of the seven DNA pieces (fresh tip for every transfer)
    for well_name in dna_wells:
        p20.transfer(1, tube_rack[well_name], dest, new_tip="always")

    # 10 uL of 2X Gibson master mix (1X final)
    p20.transfer(10, master_mix_well, dest, new_tip="always")

    # 3 uL water to 20 uL total, then mix 3 x 10 uL on the final transfer
    p20.transfer(
        3, water_well, dest, new_tip="always", mix_after=(3, 10)
    )

    # --- Incubate: 50 C for 60 minutes (after final additions/mixing) ---
    temp_module.set_temperature(50)
    ctx.delay(seconds=3600)
    temp_module.deactivate()
