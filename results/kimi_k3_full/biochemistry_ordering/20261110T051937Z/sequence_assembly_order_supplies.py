metadata = {'apiLevel': '2.19'}


def run(protocol):
    # Labware: source tube rack, tip rack, and reaction plate on temperature module
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    plate = temp_module.load_labware('opentrons_96_aluminumblock_biorad_wellplate_200ul')

    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips])

    dest = plate['A1']

    # Add nuclease-free water first (3 uL)
    pipette.transfer(3, tuberack['B3'], dest, new_tip='always')

    # Add 1 uL of each of the seven DNA pieces (fragment_001..006, backbone)
    dna_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']
    for well_name in dna_wells:
        pipette.transfer(1, tuberack[well_name], dest, new_tip='always')

    # Add 10 uL 2X Gibson master mix last and mix the final reaction
    # (3 repetitions, 10 uL) immediately after this final liquid addition
    pipette.transfer(10, tuberack['B2'], dest, new_tip='always', mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes after all additions and mixing
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
