metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent_a = tuberack['A1']
    water = tuberack['A2']

    targets = [plate['A1'], plate['A2']]

    for target in targets:
        pipette.transfer(5.0, reagent_a, target, new_tip='always')
        pipette.transfer(15.0, water, target, new_tip='always', mix_after=(3, 10))
