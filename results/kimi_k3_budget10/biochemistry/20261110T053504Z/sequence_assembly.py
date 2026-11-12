metadata = {'apiLevel': '2.19'}


def run(protocol):
    # Labware: source tube rack, 20 uL tip rack, and the reaction plate on
    # the configured temperature module.
    tube_rack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', 1)
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', 2)
    temp_module = protocol.load_module('temperature module gen2', 4)
    reaction_plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Instrument
    pipette = protocol.load_instrument('p20_single_gen2', 'left',
                                       tip_racks=[tip_rack])

    # Source wells on the tube rack
    water = tube_rack['B3']
    master_mix = tube_rack['B2']
    dna_sources = [tube_rack['A1'],  # fragment_001
                   tube_rack['A2'],  # fragment_002
                   tube_rack['A3'],  # fragment_003
                   tube_rack['A4'],  # fragment_004
                   tube_rack['A5'],  # fragment_005
                   tube_rack['A6'],  # fragment_006
                   tube_rack['B1']]  # backbone

    # Destination reaction well
    dest = reaction_plate['A1']

    # Build the 20 uL Gibson reaction: 3 uL water, 1 uL of each of the
    # seven overlap-ready DNA pieces, then 10 uL of 2X master mix last.
    pipette.transfer(3, water, dest, new_tip='always')
    for source in dna_sources:
        pipette.transfer(1, source, dest, new_tip='always')
    pipette.transfer(10, master_mix, dest, new_tip='always',
                     mix_after=(3, 10))

    # Incubate at 50 C for 60 minutes after final additions and mixing.
    temp_module.set_temperature(50)
    protocol.delay(minutes=60)
