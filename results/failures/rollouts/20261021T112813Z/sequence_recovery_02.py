metadata = {
    "protocolName": "sequence_recovery_02 seven-piece Gibson assembly",
    "author": "Opentrons OT-2 automated protocol",
    "apiLevel": "2.19",
    "description": (
        "Assemble the seven supplied overlap-ready DNA stocks (fragment_001..006 plus "
        "the backbone source remainder) into the 20 uL circular benchmark target in 4:A1 "
        "at 1X Gibson master mix, mix, then incubate at 50 C for 60 min. "
        "Constructed in-silico benchmark; no experimental validation is claimed."
    ),
}


def run(protocol):
    # Reaction design (from the task inventory):
    # 4:A1 = fragment_001..006 (1 uL each) + backbone (1 uL)
    #        + gibson_master_mix (10 uL) + water (3 uL) = 20 uL
    dna_sources = [
        ("A1", 1.0),  # fragment_001
        ("A2", 1.0),  # fragment_002
        ("A3", 1.0),  # fragment_003
        ("A4", 1.0),  # fragment_004
        ("A5", 1.0),  # fragment_005
        ("A6", 1.0),  # fragment_006
        ("B1", 1.0),  # backbone (source remainder, not an added plasmid)
    ]
    water_well = "B3"
    master_mix_well = "B2"
    water_ul = 3.0
    master_mix_ul = 10.0
    mix_cycles = 3
    mix_volume_ul = 10.0
    incubation_c = 50
    incubation_min = 60

    # Deck
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])

    reaction = plate["A1"]

    # Assemble at ambient: water first, then the seven DNA pieces, then the 2X
    # master mix last so the enzyme is added after all other components. The
    # final transfer carries the required post-addition mixing.
    p20.transfer(water_ul, tuberack[water_well], reaction, new_tip="always")

    for well, vol in dna_sources:
        p20.transfer(vol, tuberack[well], reaction, new_tip="always")

    p20.transfer(
        master_mix_ul,
        tuberack[master_mix_well],
        reaction,
        new_tip="always",
        mix_after=(mix_cycles, mix_volume_ul),
    )

    # Incubate: heating strictly after the final addition and mixing.
    # set_temperature blocks until the block reaches the setpoint.
    temp_mod.set_temperature(incubation_c)
    protocol.delay(minutes=incubation_min)
