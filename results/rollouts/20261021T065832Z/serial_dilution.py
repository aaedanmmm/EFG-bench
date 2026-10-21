metadata = {'apiLevel': '2.19'}


def run(protocol):
    # Labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips])

    # Sources
    reagent = tuberack['A1']   # reagent_A stock
    water = tuberack['A2']     # water stock

    # Plate wells
    a1 = plate['A1']
    a2 = plate['A2']
    a3 = plate['A3']
    waste = plate['A12']

    # Step 1: 20 uL reagent_A into A1
    p20.pick_up_tip()
    p20.transfer(20, reagent, a1, new_tip='never')
    p20.drop_tip()

    # Step 2: water additions with one tip.
    # Fill empty wells A2 and A3 first so the tip stays water-clean;
    # dispense into A1 (contains reagent) last, then discard the tip.
    p20.pick_up_tip()
    p20.transfer(20, water, a2, new_tip='never')
    p20.transfer(20, water, a3, new_tip='never')
    p20.transfer(20, water, a1, new_tip='never')
    p20.drop_tip()

    # Step 3: mix A1, then move 20 uL A1 -> A2
    p20.pick_up_tip()
    p20.mix(3, 10, a1)
    p20.transfer(20, a1, a2, new_tip='never')
    p20.drop_tip()

    # Step 4: mix A2, then move 20 uL A2 -> A3
    p20.pick_up_tip()
    p20.mix(3, 10, a2)
    p20.transfer(20, a2, a3, new_tip='never')
    p20.drop_tip()

    # Step 5: mix A3, then discard 20 uL A3 -> waste A12
    p20.pick_up_tip()
    p20.mix(3, 10, a3)
    p20.transfer(20, a3, waste, new_tip='never')
    p20.drop_tip()

    # Step 6: remix final wells after all transfers (fresh tip each)
    p20.pick_up_tip()
    p20.mix(3, 10, a1)
    p20.drop_tip()

    p20.pick_up_tip()
    p20.mix(3, 10, a2)
    p20.drop_tip()

    p20.pick_up_tip()
    p20.mix(3, 10, a3)
    p20.drop_tip()
