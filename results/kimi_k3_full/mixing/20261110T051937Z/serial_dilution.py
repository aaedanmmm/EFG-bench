metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    stock = tuberack['A1']  # reagent_A
    water = tuberack['A2']  # water

    a1 = plate['A1']
    a2 = plate['A2']
    a3 = plate['A3']
    waste = plate['A12']

    # 1. Add 20 uL water to each of the three target wells (single tip,
    #    only ever contacts water stock and water-only wells).
    pipette.pick_up_tip()
    pipette.aspirate(20, water)
    pipette.dispense(20, a1)
    pipette.aspirate(20, water)
    pipette.dispense(20, a2)
    pipette.aspirate(20, water)
    pipette.dispense(20, a3)
    pipette.drop_tip()

    # 2. Add 20 uL reagent stock to A1 (fresh tip, dedicated to stock).
    pipette.pick_up_tip()
    pipette.aspirate(20, stock)
    pipette.dispense(20, a1)
    pipette.drop_tip()

    # 3. Mix A1, then transfer 20 uL from A1 to A2.
    pipette.pick_up_tip()
    pipette.mix(3, 10, a1)
    pipette.aspirate(20, a1)
    pipette.dispense(20, a2)
    pipette.drop_tip()

    # 4. Mix A2, then transfer 20 uL from A2 to A3.
    pipette.pick_up_tip()
    pipette.mix(3, 10, a2)
    pipette.aspirate(20, a2)
    pipette.dispense(20, a3)
    pipette.drop_tip()

    # 5. Mix A3, then discard 20 uL from A3 to waste A12.
    pipette.pick_up_tip()
    pipette.mix(3, 10, a3)
    pipette.aspirate(20, a3)
    pipette.dispense(20, waste)
    pipette.drop_tip()

    # 6. Remix the three final wells after all transfers (fresh tips).
    for well in [a1, a2, a3]:
        pipette.pick_up_tip()
        pipette.mix(3, 10, well)
        pipette.drop_tip()
