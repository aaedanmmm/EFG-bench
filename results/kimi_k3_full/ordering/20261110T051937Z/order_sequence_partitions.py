metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips])

    dest = plate['A1']

    dna_sources = [
        tuberack['A1'],
        tuberack['A2'],
        tuberack['A3'],
        tuberack['A4'],
        tuberack['A5'],
        tuberack['A6'],
        tuberack['B1'],
    ]
    for src in dna_sources:
        pipette.transfer(2, src, dest, new_tip='always')

    pipette.transfer(6, tuberack['B2'], dest, new_tip='always', mix_after=(3, 10))
