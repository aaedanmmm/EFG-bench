from opentrons import protocol_api

metadata = {
    'protocolName': 'sequence_recovery_01 seven-piece Gibson assembly',
    'description': ('Assemble fragment_001..fragment_006 + backbone with 2X '
                    'Gibson master mix; incubate 50 C for 60 min.'),
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
    rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 1)
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', 2)
    temp_module = protocol.load_module('temperature module gen2', 4)
    plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips])

    dest = plate['A1']

    # Source wells on the tube rack (slot 1)
    dna_wells = [
        rack['A1'],  # fragment_001
        rack['A2'],  # fragment_002
        rack['A3'],  # fragment_003
        rack['A4'],  # fragment_004
        rack['A5'],  # fragment_005
        rack['A6'],  # fragment_006
        rack['B1'],  # backbone
    ]
    master_mix = rack['B2']  # 2X Gibson master mix
    water = rack['B3']

    # Add 1 uL of each DNA piece; fresh tip every transfer to avoid carryover.
    for well in dna_wells:
        p20.transfer(1, well, dest, new_tip='always')

    # Add 10 uL of 2X Gibson master mix (1X final in 20 uL).
    p20.transfer(10, master_mix, dest, new_tip='always')

    # Add 3 uL water to reach 20 uL total, then mix 3 x 10 uL.
    # The tip is empty after the dispense, so mix_after is valid here.
    p20.transfer(3, water, dest, new_tip='always', mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes AFTER all additions and mixing.
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
