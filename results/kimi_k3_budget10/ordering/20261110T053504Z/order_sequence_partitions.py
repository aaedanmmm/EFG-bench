metadata = {'apiLevel': '2.19'}


def run(protocol):
    rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pipette = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tips])

    dest = plate['A1']

    dna_sources = [
        rack['A1'],
        rack['A2'],
        rack['A3'],
        rack['A4'],
        rack['A5'],
        rack['A6'],
        rack['B1'],
    ]

    for source_well in dna_sources:
        pipette.transfer(2, source_well, dest, new_tip='always')

    pipette.transfer(6, rack['B2'], dest, new_tip='always', mix_after=(3, 10))
