from opentrons import protocol_api

metadata = {
    'protocolName': 'Seven-piece Gibson assembly (sequence_recovery_01)',
    'author': 'benchmark',
    'description': 'Assemble fragment_001..fragment_006 + backbone with 2X Gibson master mix, 50 C x 60 min',
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_mod = protocol.load_module('temperature module gen2', '4')
    plate = temp_mod.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    # Source wells on the tube rack
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']  # 6 fragments + backbone
    master_mix = tuberack['B2']
    water = tuberack['B3']

    # Reaction well on the temperature module plate
    dest = plate['A1']

    # Add 3 uL water
    p20.transfer(3, water, dest)

    # Add 1 uL of each DNA piece (0.03 pmol each at stock concentrations)
    for well in dna_wells:
        p20.transfer(1, tuberack[well], dest)

    # Add 10 uL 2X master mix last (1X final in 20 uL) and mix 3 x 10 uL
    p20.transfer(10, master_mix, dest, mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes after final additions/mixing
    temp_mod.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_mod.deactivate()
