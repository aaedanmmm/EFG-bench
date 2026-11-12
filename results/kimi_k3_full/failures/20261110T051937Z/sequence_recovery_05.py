metadata = {
    'protocolName': 'Seven-piece Gibson assembly (sequence_recovery_05)',
    'description': ('Stitch fragment_001..fragment_006 and backbone into the '
                    'circular 12484 bp benchmark product: 1 uL of each of the '
                    'seven overlap-ready DNA stocks, 10 uL 2X Gibson master '
                    'mix and 3 uL water (20 uL total), mix 3 x 10 uL, then '
                    'incubate at 50 C for 60 min.'),
    'apiLevel': '2.19',
}


def run(protocol):
    # Deck labware
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')

    # Temperature module gen2 in slot 4 carrying the reaction plate
    temp_module = protocol.load_module('temperature module gen2', '4')
    plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Single-channel P20 on the left mount
    p20 = protocol.load_instrument(
        'p20_single_gen2', 'left', tip_racks=[tiprack])

    # Source wells in the slot-1 tuberack:
    # A1..A6 = fragment_001..fragment_006, B1 = backbone (source remainder),
    # B2 = 2X Gibson master mix, B3 = nuclease-free water.
    dest = plate['A1']

    # 1 uL of each of the seven DNA pieces (0.03 pmol each at the
    # constructed stock concentrations); fresh tip for every transfer.
    for well in ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1']:
        p20.transfer(1, tuberack[well], dest, new_tip='always')

    # 10 uL of 2X Gibson master mix -> 1X final in the 20 uL reaction
    p20.transfer(10, tuberack['B2'], dest, new_tip='always')

    # 3 uL water to bring the reaction to 20 uL
    p20.transfer(3, tuberack['B3'], dest, new_tip='always')

    # Mix 3 x 10 uL with a fresh, initially empty tip AFTER the last
    # liquid change.
    p20.pick_up_tip()
    p20.mix(3, 10, dest)
    p20.drop_tip()

    # Incubate at 50 C for exactly 60 minutes. Heating follows the final
    # additions and mixing.
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
