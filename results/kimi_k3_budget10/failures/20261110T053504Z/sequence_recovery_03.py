from opentrons import protocol_api

metadata = {
    'protocolName': 'Seven-piece Gibson assembly (sequence_recovery_03)',
    'author': 'OT-2 benchmark',
    'description': ('Assemble fragment_001..fragment_006 and backbone with 2X '
                    'Gibson master mix into the circular benchmark target; '
                    'mix and incubate at 50 C for 60 minutes.'),
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    reaction_plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    # Source wells on the tube rack (slot 1)
    dna_sources = [
        tuberack['A1'],  # fragment_001
        tuberack['A2'],  # fragment_002
        tuberack['A3'],  # fragment_003
        tuberack['A4'],  # fragment_004
        tuberack['A5'],  # fragment_005
        tuberack['A6'],  # fragment_006
        tuberack['B1'],  # backbone
    ]
    master_mix = tuberack['B2']  # 2X Gibson master mix
    water = tuberack['B3']       # nuclease-free water

    reaction = reaction_plate['A1']

    # Add 1 uL of each DNA piece, fresh tip for every stock
    for src in dna_sources:
        p20.pick_up_tip()
        p20.aspirate(1, src)
        p20.dispense(1, reaction)
        p20.drop_tip()

    # Add 10 uL of 2X Gibson master mix (1X final in 20 uL)
    p20.pick_up_tip()
    p20.aspirate(10, master_mix)
    p20.dispense(10, reaction)
    p20.drop_tip()

    # Add 3 uL water to reach 20 uL total, then mix 3 x 10 uL
    p20.pick_up_tip()
    p20.aspirate(3, water)
    p20.dispense(3, reaction)
    p20.mix(3, 10, reaction)
    p20.drop_tip()

    # Incubate at 50 C for 60 minutes after final additions and mixing
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
