from opentrons import protocol_api

metadata = {
    "protocolName": "Seven-piece Gibson assembly: fragment_001..006 + backbone, 50C 60min",
    "apiLevel": "2.19",
}


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    temp_mod = protocol.load_module("temperature module gen2", "4")
    plate = temp_mod.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")

    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])

    dest = plate["A1"]

    # Sources (slot 1 tube rack)
    water = tuberack["B3"]
    master_mix = tuberack["B2"]
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]  # fragment_001..006, backbone

    # 1) Water first (3 uL)
    pipette.transfer(3, water, dest, new_tip="always")

    # 2) 1 uL of each of the seven DNA pieces (fresh tip each)
    for well in dna_wells:
        pipette.transfer(1, tuberack[well], dest, new_tip="always")

    # 3) 2X Gibson master mix last (10 uL), then mix 3 x 10 uL
    pipette.transfer(10, master_mix, dest, new_tip="always", mix_after=(3, 10))

    # 4) Incubate at 50 C for exactly 60 minutes, then release the module
    temp_mod.set_temperature(50)
    protocol.delay(minutes=60)
    temp_mod.deactivate()
