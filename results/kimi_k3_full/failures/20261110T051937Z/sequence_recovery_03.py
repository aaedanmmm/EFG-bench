from opentrons import protocol_api

metadata = {
    'protocolName': 'sequence_recovery_03 seven-piece Gibson assembly',
    'author': 'benchmark',
    'description': (
        'Assemble fragment_001..fragment_006 + backbone (1 uL each) with '
        '10 uL 2X Gibson master mix and 3 uL water (20 uL total); mix 3x10 uL; '
        'incubate at 50 C for 60 min on temperature module gen2.'
    ),
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    dest = plate['A1']

    water = tuberack['B3']
    master_mix = tuberack['B2']
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']

    # 1) Water (3 uL)
    pipette.transfer(3, water, dest, new_tip='always')

    # 2) Seven DNA pieces, 1 uL each (fragment_001..fragment_006, backbone)
    for well in dna_wells:
        pipette.transfer(1, tuberack[well], dest, new_tip='always')

    # 3) 2X Gibson master mix (10 uL) last, then mix 3 x 10 uL
    pipette.transfer(10, master_mix, dest, new_tip='always',
                     mix_after=(3, 10))

    # 4) Incubate: heat block to 50 C (blocking), hold 60 min, then release
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
