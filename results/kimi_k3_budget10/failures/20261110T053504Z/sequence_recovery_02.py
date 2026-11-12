metadata = {
    "protocolName": "Seven-piece Gibson assembly (sequence_recovery_02)",
    "author": "benchmark",
    "description": (
        "Assemble fragment_001..fragment_006 + backbone (1 uL each) with "
        "10 uL 2X Gibson master mix and 3 uL water in 4:A1; mix 3 x 10 uL; "
        "incubate at 50 C for 60 minutes."
    ),
    "apiLevel": "2.19",
}


def run(protocol):
    # Labware
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_module = protocol.load_module("temperature module gen2", 4)
    plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    # Pipette
    p20 = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tiprack]
    )

    dest = plate["A1"]

    # DNA source wells: 1 uL each, fresh tip per stock to avoid carryover
    dna_wells = [
        tuberack["A1"],  # fragment_001
        tuberack["A2"],  # fragment_002
        tuberack["A3"],  # fragment_003
        tuberack["A4"],  # fragment_004
        tuberack["A5"],  # fragment_005
        tuberack["A6"],  # fragment_006
        tuberack["B1"],  # backbone (source remainder)
    ]
    for well in dna_wells:
        p20.transfer(1, well, dest, new_tip="always")

    # 10 uL 2X Gibson master mix (final 1X in 20 uL)
    p20.transfer(10, tuberack["B2"], dest, new_tip="always")

    # 3 uL water to 20 uL total; mix the finished reaction 3 x 10 uL
    p20.transfer(3, tuberack["B3"], dest, new_tip="always", mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes AFTER final additions and mixing
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
