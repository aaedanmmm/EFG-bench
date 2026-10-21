metadata = {'apiLevel': '2.19'}


def run(protocol):
    tube_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    reaction_plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tip_rack])

    backbone = tube_rack['A1']
    insert_a = tube_rack['A2']
    insert_b = tube_rack['A3']
    master_mix = tube_rack['A4']
    water = tube_rack['A5']
    reaction = reaction_plate['A1']

    # Add components; fresh tip for each stock to avoid carryover.
    pipette.transfer(5, water, reaction, new_tip='always')
    pipette.transfer(1, backbone, reaction, new_tip='always')
    pipette.transfer(2, insert_a, reaction, new_tip='always')
    pipette.transfer(2, insert_b, reaction, new_tip='always')
    # Master mix added last; mix 3 x 10 uL immediately after this final
    # liquid change.
    pipette.transfer(10, master_mix, reaction, new_tip='always',
                     mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes after all additions and mixing.
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
    temp_module.deactivate()
