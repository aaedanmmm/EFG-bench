metadata = {'apiLevel': '2.19'}


def run(protocol):
    # Labware
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    # Pipette
    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    # Sources
    source_a = tuberack['A1']  # reagent_A
    source_b = tuberack['A2']  # reagent_B
    source_w = tuberack['A3']  # water

    # Targets
    target_a1 = plate['A1']
    target_a2 = plate['A2']
    target_a3 = plate['A3']

    targets = [target_a1, target_a2, target_a3]
    vols_a = [2.0, 4.0, 6.0]
    vols_b = [3.0, 6.0, 9.0]
    vols_w = [15.0, 10.0, 5.0]

    # Step 1: reagent_A to all three (initially empty) targets with one tip.
    # Wells contain only reagent_A at this point, so no mixture is touched and
    # the tip never returns to any stock after dispensing.
    pipette.pick_up_tip()
    pipette.aspirate(12.0, source_a)
    for well, vol in zip(targets, vols_a):
        pipette.dispense(vol, well)
    pipette.drop_tip()

    # Step 2: reagent_B to all three targets with one fresh tip.
    # The tip never returns to a stock after contacting destination contents.
    pipette.pick_up_tip()
    pipette.aspirate(18.0, source_b)
    for well, vol in zip(targets, vols_b):
        pipette.dispense(vol, well)
    pipette.drop_tip()

    # Step 3: water is the final component for each target. Each transfer uses
    # a fresh tip and mixes that target (3 repetitions of 10 uL) immediately
    # after its last liquid change via mix_after.
    for well, vol in zip(targets, vols_w):
        pipette.transfer(vol, source_w, well, new_tip='always', mix_after=(3, 10))
