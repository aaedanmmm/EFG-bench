metadata = {'apiLevel': '2.19'}


def run(protocol):
    # Labware
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    # Source wells
    reagent = tuberack['A1']  # reagent_A stock
    water = tuberack['A2']    # water stock

    # Plate wells
    a1 = plate['A1']
    a2 = plate['A2']
    a3 = plate['A3']
    waste = plate['A12']

    # Step 1: add 20 uL water to A1, A2, A3 (single tip; only touches
    # the water stock and initially empty wells)
    p20.pick_up_tip()
    for well in [a1, a2, a3]:
        p20.aspirate(20, water)
        p20.dispense(20, well)
    p20.drop_tip()

    # Step 2: add 20 uL reagent_A stock to A1 (fresh tip, no carryover)
    p20.pick_up_tip()
    p20.aspirate(20, reagent)
    p20.dispense(20, a1)
    p20.drop_tip()

    # Step 3: mix A1, then transfer 20 uL A1 -> A2
    p20.pick_up_tip()
    p20.mix(3, 10, a1)
    p20.aspirate(20, a1)
    p20.dispense(20, a2)
    p20.drop_tip()

    # Step 4: mix A2, then transfer 20 uL A2 -> A3
    p20.pick_up_tip()
    p20.mix(3, 10, a2)
    p20.aspirate(20, a2)
    p20.dispense(20, a3)
    p20.drop_tip()

    # Step 5: mix A3, then discard 20 uL A3 -> waste A12
    p20.pick_up_tip()
    p20.mix(3, 10, a3)
    p20.aspirate(20, a3)
    p20.dispense(20, waste)
    p20.drop_tip()

    # Step 6: remix the final wells after all transfers (fresh tips)
    for well in [a1, a2, a3]:
        p20.pick_up_tip()
        p20.mix(3, 10, well)
        p20.drop_tip()
