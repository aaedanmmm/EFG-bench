metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent = tuberack['A1']
    water = tuberack['A2']
    targets = [plate['A1'], plate['A2']]

    # Add 5 uL reagent_A to each target with one tip:
    # a single 10 uL aspirate split into two 5 uL dispenses (no return to stock).
    pipette.pick_up_tip()
    pipette.aspirate(10.0, reagent)
    for target in targets:
        pipette.dispense(5.0, target)
    pipette.drop_tip()

    # Add 15 uL water to each target with a fresh tip, mixing (3 x 10 uL)
    # immediately after this final liquid addition.
    for target in targets:
        pipette.transfer(15.0, water, target, new_tip='always', mix_after=(3, 10))
