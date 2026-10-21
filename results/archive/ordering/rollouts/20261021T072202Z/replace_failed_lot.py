metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent = tuberack['A1']
    water = tuberack['A2']
    dest_a1 = plate['A1']
    dest_a2 = plate['A2']

    # Tip 1: dispense reagent_A into both targets (targets hold only reagent here)
    pipette.pick_up_tip()
    pipette.aspirate(10.0, reagent)
    pipette.dispense(5.0, dest_a1)
    pipette.dispense(5.0, dest_a2)
    pipette.drop_tip()

    # Tip 2: water into A1, then mix A1 after its last liquid change
    pipette.pick_up_tip()
    pipette.aspirate(15.0, water)
    pipette.dispense(15.0, dest_a1)
    pipette.mix(3, 10.0, dest_a1)
    pipette.drop_tip()

    # Tip 3: water into A2, then mix A2 after its last liquid change
    pipette.pick_up_tip()
    pipette.aspirate(15.0, water)
    pipette.dispense(15.0, dest_a2)
    pipette.mix(3, 10.0, dest_a2)
    pipette.drop_tip()
