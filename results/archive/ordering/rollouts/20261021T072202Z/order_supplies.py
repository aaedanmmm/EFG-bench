metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent = tuberack['A1']
    water = tuberack['A2']

    # Tip 1: water only. Water is added first into empty wells, so this tip
    # never contacts a mixture and never enters a different stock.
    pipette.pick_up_tip()
    pipette.transfer(15.0, water, plate['A1'], new_tip='never')
    pipette.transfer(15.0, water, plate['A2'], new_tip='never')
    pipette.drop_tip()

    # Tip 2: reagent only. Aspirate 10 uL once (no return to stock after
    # touching a mixture), dispense 5 uL into each well, then mix each well
    # after its last liquid change.
    pipette.pick_up_tip()
    pipette.aspirate(10.0, reagent)
    pipette.dispense(5.0, plate['A1'])
    pipette.dispense(5.0, plate['A2'])
    pipette.mix(3, 10, plate['A1'])
    pipette.mix(3, 10, plate['A2'])
    pipette.drop_tip()
