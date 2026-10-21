metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    plate = temp_module.load_labware('opentrons_96_aluminumblock_biorad_wellplate_200ul')

    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    backbone = tuberack['A1']
    insert_a = tuberack['A2']
    insert_b = tuberack['A3']
    master_mix = tuberack['A4']
    water = tuberack['A5']
    dest = plate['A1']

    pipette.transfer(5, water, dest, new_tip='always')
    pipette.transfer(1, backbone, dest, new_tip='always')
    pipette.transfer(2, insert_a, dest, new_tip='always')
    pipette.transfer(2, insert_b, dest, new_tip='always')
    pipette.transfer(10, master_mix, dest, new_tip='always', mix_after=(3, 10))

    temp_module.set_temperature(50)
    protocol.delay(seconds=1800)
    temp_module.deactivate()
