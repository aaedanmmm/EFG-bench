metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent_a = tuberack['A1']
    water = tuberack['A2']
    targets = [plate['A1'], plate['A2']]

    # Add 15 uL water to each target with a single tip.
    # Wells start empty, so this tip only ever contacts water.
    p20.pick_up_tip()
    for well in targets:
        p20.aspirate(15, water)
        p20.dispense(15, well)
    p20.drop_tip()

    # Add 5 uL reagent A to each target with a fresh tip per well,
    # then mix 3 x 10 uL immediately after the final liquid addition.
    for well in targets:
        p20.pick_up_tip()
        p20.aspirate(5, reagent_a)
        p20.dispense(5, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
