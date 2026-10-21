from opentrons import protocol_api

metadata = {"protocolName": "sequence_recovery_04 seven piece Gibson assembly", "author": "benchmark", "apiLevel": "2.19"}


def run(protocol):
    reaction_well = "A1"
    water_well = "B3"
    master_mix_well = "B2"
    dna_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]
    water_ul = 3.0
    dna_ul = 1.0
    master_mix_ul = 10.0
    mix_cycles = 3
    mix_volume_ul = 10.0
    incubation_c = 50.0
    incubation_seconds = 3600

    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    reaction = plate[reaction_well]

    p20.transfer(water_ul, rack[water_well], reaction, new_tip="always")
    for well in dna_wells:
        p20.transfer(dna_ul, rack[well], reaction, new_tip="always")
    p20.transfer(master_mix_ul, rack[master_mix_well], reaction, new_tip="always", mix_after=(mix_cycles, mix_volume_ul))

    temp_mod.set_temperature(incubation_c)
    protocol.delay(seconds=incubation_seconds)
