from opentrons import protocol_api

metadata = {
    'protocolName': 'Seven-piece Gibson assembly (sequence_recovery_03)',
    'description': 'Assemble fragment_001..006 + backbone with 2X Gibson master mix, incubate 50 C for 60 min',
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    reaction_plate = temp_module.load_labware('opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    dest = reaction_plate['A1']

    # DNA pieces: 1 uL each (fresh tip per transfer, dropped after use)
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']
    for well in dna_wells:
        p20.transfer(1, tuberack[well], dest)

    # 2X Gibson master mix: 10 uL (1X final in 20 uL)
    p20.transfer(10, tuberack['B2'], dest)

    # Water: 3 uL, then mix the complete 20 uL reaction 3x with 10 uL
    p20.transfer(3, tuberack['B3'], dest, mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes (heating follows final additions/mixing)
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
