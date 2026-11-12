from opentrons import protocol_api

metadata = {
    'protocolName': 'sequence_recovery_04 seven-piece Gibson assembly',
    'author': 'benchmark',
    'description': 'Assemble fragment_001..006 + backbone into the 12484 bp circular target',
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')

    # Temperature module gen2 in slot 4 with the reaction plate
    temp_mod = protocol.load_module('temperature module gen2', '4')
    plate = temp_mod.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    pip = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    reaction = plate['A1']

    # Seven DNA pieces, 1 uL each (0.03 pmol per piece at stock concentrations)
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']
    for well in dna_wells:
        pip.transfer(1, tuberack[well], reaction, new_tip='always')

    # 2X Gibson master mix, 10 uL -> 1X final in 20 uL
    pip.transfer(10, tuberack['B2'], reaction, new_tip='always')

    # Nuclease-free water, 3 uL, then mix 3 x 10 uL after the final addition
    pip.transfer(3, tuberack['B3'], reaction,
                 mix_after=(3, 10), new_tip='always')

    # Incubate at 50 C for 60 minutes (3600 s) after final additions/mixing
    temp_mod.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_mod.deactivate()
