"""Constructed synthetic benchmark reference; not a wet-lab validation."""
from opentrons import protocol_api
metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    stock = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    temperature = protocol.load_module("temperature module gen2", "4")
    plate = temperature.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")
    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    pipette.transfer(5, stock["A5"], plate["A1"])
    pipette.transfer(10, stock["A4"], plate["A1"])
    pipette.transfer(1, stock["A1"], plate["A1"])
    pipette.transfer(2, stock["A2"], plate["A1"])
    pipette.transfer(2, stock["A3"], plate["A1"], mix_after=(3, 10))
    temperature.set_temperature(50)
    protocol.delay(minutes=60)
    temperature.deactivate()
