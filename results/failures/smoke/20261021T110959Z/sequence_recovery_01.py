from opentrons import protocol_api

metadata = {
    'protocolName': 'Seven-piece Gibson assembly (sequence_recovery_01)',
    'author': 'benchmark',
    'description': 'Assemble fragment_001..fragment_006 + backbone with 2X Gibson master mix, incubate 50 C for 60 min.',
    'apiLevel': '2.19',
}


def run(protocol: protocol_api.ProtocolContext):
    # Deck labware
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '1')
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    temp_module = protocol.load_module('temperature module gen2', '4')
    reaction_plate = temp_module.load_labware(
        'opentrons_96_aluminumblock_biorad_wellplate_200ul')

    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    # Source wells (slot 1 tube rack)
    fragment_001 = tuberack['A1']
    fragment_002 = tuberack['A2']
    fragment_003 = tuberack['A3']
    fragment_004 = tuberack['A4']
    fragment_005 = tuberack['A5']
    fragment_006 = tuberack['A6']
    backbone = tuberack['B1']
    gibson_master_mix = tuberack['B2']
    water = tuberack['B3']

    dest = reaction_plate['A1']

    # 20 uL reaction: 7 DNA pieces at 1 uL each, 10 uL 2X master mix, 3 uL water.
    additions = [
        (fragment_001, 1),
        (fragment_002, 1),
        (fragment_003, 1),
        (fragment_004, 1),
        (fragment_005, 1),
        (fragment_006, 1),
        (backbone, 1),
        (gibson_master_mix, 10),
        (water, 3),
    ]

    # Fresh tip for every stock to avoid carryover; drop each tip after use.
    for source, volume in additions[:-1]:
        p20.transfer(volume, source, dest, new_tip='always')

    # Final addition, then mix 3 x 10 uL with the same tip before dropping it.
    last_source, last_volume = additions[-1]
    p20.transfer(last_volume, last_source, dest,
                 mix_after=(3, 10), new_tip='always')

    # Incubate at 50 C for 60 minutes (3600 seconds), after all additions/mixing.
    temp_module.set_temperature(50)
    protocol.delay(seconds=3600)
    temp_module.deactivate()
