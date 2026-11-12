metadata = {
    "protocolName": "sequence_recovery_02 seven-piece Gibson assembly",
    "description": (
        "Combine 1 uL each of fragment_001..fragment_006 and backbone with "
        "10 uL 2X Gibson master mix and 3 uL water (20 uL total) in the "
        "temperature-module plate, mix 3 x 10 uL, then incubate at 50 C "
        "for 60 minutes."
    ),
    "author": "benchmark",
    "apiLevel": "2.19",
}


def run(protocol):
    # Deck labware
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_module = protocol.load_module("temperature module gen2", 4)
    reaction_plate = temp_module.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    p20 = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tiprack]
    )

    reaction = reaction_plate.wells_by_name()["A1"]

    # Seven DNA pieces, 1 uL each, fresh tip per stock to avoid carryover:
    # A1=fragment_001, A2=fragment_002, A3=fragment_003, A4=fragment_004,
    # A5=fragment_005, A6=fragment_006, B1=backbone
    for well_name in ("A1", "A2", "A3", "A4", "A5", "A6", "B1"):
        p20.transfer(
            1,
            tuberack.wells_by_name()[well_name],
            reaction,
            new_tip="always",
        )

    # 10 uL of 2X Gibson master mix -> 1X final in the 20 uL reaction
    p20.transfer(
        10,
        tuberack.wells_by_name()["B2"],
        reaction,
        new_tip="always",
    )

    # 3 uL nuclease-free water completes 20 uL; mix 3 x 10 uL immediately
    # after this final liquid addition.
    p20.transfer(
        3,
        tuberack.wells_by_name()["B3"],
        reaction,
        new_tip="always",
        mix_after=(3, 10),
    )

    # Incubate at 50 C for 60 minutes (3600 s) after all additions/mixing.
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
