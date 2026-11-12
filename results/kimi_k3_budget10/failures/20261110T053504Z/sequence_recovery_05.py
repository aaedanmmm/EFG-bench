from opentrons import protocol_api

metadata = {
    "protocolName": "sequence_recovery_05_gibson_7piece",
    "author": "benchmark",
    "description": (
        "Seven-piece Gibson assembly of fragment_001..fragment_006 and "
        "backbone into the circular 12484 bp benchmark target. 20 uL "
        "reaction: 1 uL each DNA piece, 10 uL 2X Gibson master mix, "
        "3 uL water; mixed 3 x 10 uL; incubated 50 C for 60 min."
    ),
    "apiLevel": "2.19",
}


def run(protocol):
    # Labware
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 1
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    # Pipette
    p20 = protocol.load_instrument(
        "p20_single_gen2", "left", tip_racks=[tiprack]
    )

    dest = plate.wells_by_name()["A1"]

    # Add the seven DNA pieces, 1 uL each (fresh tip per stock).
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    for well_name in dna_wells:
        p20.transfer(
            1,
            tuberack.wells_by_name()[well_name],
            dest,
            new_tip="always",
        )

    # Add nuclease-free water, 3 uL.
    p20.transfer(
        3,
        tuberack.wells_by_name()["B3"],
        dest,
        new_tip="always",
    )

    # Add 2X Gibson master mix last, 10 uL, then mix 3 x 10 uL.
    p20.transfer(
        10,
        tuberack.wells_by_name()["B2"],
        dest,
        new_tip="always",
        mix_after=(3, 10),
    )

    # Incubate at 50 C for 60 minutes (heating follows final
    # additions and mixing), then cool down.
    temp_mod.set_temperature(50)
    protocol.delay(minutes=60)
    temp_mod.deactivate()
