metadata = {'apiLevel': '2.19'}


def run(protocol):
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')

    pipette = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    reagent_a = tuberack['A1']
    reagent_b = tuberack['A2']
    water = tuberack['A3']

    target_wells = ['A1', 'A2', 'A3']
    water_vols = [15.0, 10.0, 5.0]
    reagent_a_vols = [2.0, 4.0, 6.0]
    reagent_b_vols = [3.0, 6.0, 9.0]

    for i in range(3):
        dest = plate[target_wells[i]]
        # Fresh tip for every transfer: no stock or well cross-contamination.
        pipette.transfer(water_vols[i], water, dest, new_tip='always')
        pipette.transfer(reagent_a_vols[i], reagent_a, dest,
                         new_tip='always')
        # Final liquid addition to this well mixes it afterwards.
        pipette.transfer(reagent_b_vols[i], reagent_b, dest,
                         new_tip='always', mix_after=(3, 10))

    protocol.comment('Three-reagent panel complete: 9 tips used.')
