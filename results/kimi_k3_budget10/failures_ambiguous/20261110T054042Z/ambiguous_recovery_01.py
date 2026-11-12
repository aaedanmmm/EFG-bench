from opentrons import protocol_api

metadata = {
    'protocolName': 'Seven-piece Gibson assembly (constructed benchmark)',
    'author': 'benchmark',
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tube_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', 1)
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', 2)

    temp_module = protocol.load_module('temperature module gen2', 4)
    reaction_plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    pipette = protocol.load_instrument(
        'p20_single_gen2', mount='left', tip_racks=[tip_rack])

    dest = reaction_plate['A1']

    # DNA pieces: 1 uL each (fragment_001..fragment_006, backbone)
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']
    for well in dna_wells:
        pipette.transfer(1, tube_rack[well], dest, new_tip='always')

    # 2X Gibson master mix: 10 uL (final 1X in 20 uL)
    pipette.transfer(10, tube_rack['B2'], dest, new_tip='always')

    # Water: 3 uL, then mix 3 x 10 uL with the same (now empty) tip
    pipette.transfer(3, tube_rack['B3'], dest, new_tip='always',
                     mix_after=(3, 10))

    # Incubate at 50 C for exactly 60 minutes after final additions/mixing
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
