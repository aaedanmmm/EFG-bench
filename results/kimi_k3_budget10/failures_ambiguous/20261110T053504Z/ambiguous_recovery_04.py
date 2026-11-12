from opentrons import protocol_api

metadata = {
    'protocolName': 'Seven-piece Gibson assembly (ambiguous_recovery_04)',
    'author': 'benchmark',
    'description': ('Assemble fragment_001..fragment_006 + backbone with 2X Gibson '
                    'master mix into a circular 12484 bp product; 20 uL reaction, '
                    '50 C for 60 min on temperature module gen2.'),
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    reaction_plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    dest = reaction_plate['A1']

    # Source wells on the tube rack (slot 1)
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']  # 6 fragments + backbone
    water_well = tuberack['B3']
    master_mix_well = tuberack['B2']

    # Add 3 uL nuclease-free water first
    pipette.transfer(3, water_well, dest, new_tip='always')

    # Add 1 uL of each of the seven DNA pieces (0.03 pmol each)
    for well_name in dna_wells:
        pipette.transfer(1, tuberack[well_name], dest, new_tip='always')

    # Add 10 uL 2X Gibson master mix last (1X final), then mix 3 x 10 uL
    pipette.transfer(10, master_mix_well, dest, new_tip='always',
                     mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes AFTER final additions and mixing
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
