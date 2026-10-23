metadata = {'apiLevel': '2.19'}


def run(protocol):
    rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent_a = rack['A1']
    water = rack['A2']
    targets = [plate['A1'], plate['A2']]

    # Step 1: add 5 uL reagent A to each initially empty target well.
    # One tip suffices: it only contacts reagent A stock and empty wells.
    pipette.pick_up_tip()
    for well in targets:
        pipette.aspirate(5.0, reagent_a)
        pipette.dispense(5.0, well)
    pipette.drop_tip()

    # Step 2: add 15 uL water to each target (last liquid change),
    # then mix 3 x 10 uL. Fresh tip per well to avoid carryover.
    for well in targets:
        pipette.pick_up_tip()
        pipette.aspirate(15.0, water)
        pipette.dispense(15.0, well)
        pipette.mix(3, 10, well)
        pipette.drop_tip()
