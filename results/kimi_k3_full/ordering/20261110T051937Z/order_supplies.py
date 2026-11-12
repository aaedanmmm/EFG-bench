metadata = {'apiLevel': '2.19'}


def run(protocol):
    tube_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tip_rack])

    reagent = tube_rack['A1']
    water = tube_rack['A2']
    targets = [plate['A1'], plate['A2']]

    # Reagent_A: 5 uL to each target. Single 10 uL aspiration split into
    # two 5 uL dispenses; the tip never returns to stock after dispensing.
    pipette.pick_up_tip()
    pipette.aspirate(10.0, reagent)
    for target in targets:
        pipette.dispense(5.0, target)
    pipette.drop_tip()

    # Water: 15 uL to each target with a fresh tip per target, mixing
    # (3 x 10 uL) immediately after this final liquid addition.
    for target in targets:
        pipette.pick_up_tip()
        pipette.transfer(15.0, water, target, new_tip='never',
                         mix_after=(3, 10))
        pipette.drop_tip()
