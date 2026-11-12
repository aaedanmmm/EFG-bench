metadata = {'apiLevel': '2.19'}


def run(protocol):
    # Labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    # Destination reaction well on the temperature block
    dest = plate['A1']

    # Add water first
    pipette.transfer(3, tuberack['B3'], dest, new_tip='always')

    # Add the seven DNA pieces (1 uL each, equimolar 0.03 pmol stocks)
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']
    for well_name in dna_wells:
        pipette.transfer(1, tuberack[well_name], dest, new_tip='always')

    # Add 2X Gibson master mix last and mix the completed reaction
    pipette.transfer(10, tuberack['B2'], dest, new_tip='always',
                     mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes (after final additions and mixing)
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
