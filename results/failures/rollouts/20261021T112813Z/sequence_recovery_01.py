from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly (sequence_recovery_01)",
    "author": "benchmark",
    "description": "Stitch fragment_001-006 plus backbone into the circular benchmark target",
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Target 4:A1 (20 uL total):
    #   water 3 uL + 2X gibson_master_mix 10 uL (1X final)
    #   + 1 uL each of fragment_001..006 and backbone (0.03 pmol each)
    # Mix 3 x 10 uL after the final addition, then incubate 50 C for 60 min.
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6"]  # fragment_001..006
    backbone_well = "B1"
    master_mix_well = "B2"
    water_well = "B3"

    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)

    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    dest = plate["A1"]

    # 1) water
    p20.transfer(3, tuberack[water_well], dest, new_tip="always")

    # 2) 2X master mix -> 1X final in 20 uL
    p20.transfer(10, tuberack[master_mix_well], dest, new_tip="always")

    # 3) each DNA piece, 1 uL (0.03 pmol each)
    for well in dna_wells:
        p20.transfer(1, tuberack[well], dest, new_tip="always")

    # 4) backbone last, with the required post-addition mixing (3 x 10 uL)
    p20.transfer(1, tuberack[backbone_well], dest, new_tip="always",
                 mix_after=(3, 10))

    # 5) heat only after all additions and mixing are complete
    temp_mod.set_temperature(50)
    protocol.delay(minutes=60)
