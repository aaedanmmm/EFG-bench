metadata = {'apiLevel': '2.19'}


def run(protocol):
    rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips])

    stock_a = rack['A1']
    stock_b = rack['A2']
    stock_w = rack['A3']

    well_a1 = plate['A1']
    well_a2 = plate['A2']
    well_a3 = plate['A3']

    # Reagent A: 2, 4, 6 uL into empty targets (total 12 uL, single aspiration)
    p20.pick_up_tip()
    p20.aspirate(12, stock_a)
    p20.dispense(2, well_a1)
    p20.dispense(4, well_a2)
    p20.dispense(6, well_a3)
    p20.drop_tip()

    # Reagent B: 3, 6, 9 uL (total 18 uL, single aspiration)
    p20.pick_up_tip()
    p20.aspirate(18, stock_b)
    p20.dispense(3, well_a1)
    p20.dispense(6, well_a2)
    p20.dispense(9, well_a3)
    p20.drop_tip()

    # Water: 15 uL to A1 and 5 uL to A3 (total 20 uL), then mix both targets
    p20.pick_up_tip()
    p20.aspirate(20, stock_w)
    p20.dispense(15, well_a1)
    p20.dispense(5, well_a3)
    p20.mix(3, 10, well_a1)
    p20.mix(3, 10, well_a3)
    p20.drop_tip()

    # Water: 10 uL to A2, then mix
    p20.pick_up_tip()
    p20.aspirate(10, stock_w)
    p20.dispense(10, well_a2)
    p20.mix(3, 10, well_a2)
    p20.drop_tip()
