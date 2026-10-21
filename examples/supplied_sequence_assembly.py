"""Constructed seven-input reference; raw-derived overlaps prepared in advance."""
from opentrons import protocol_api
metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    stock = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    temperature = protocol.load_module("temperature module gen2", "4")
    plate = temperature.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")
    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    pipette.transfer(3, stock["B3"], plate["A1"])
    pipette.transfer(10, stock["B2"], plate["A1"])
    for well in ["A1", "A2", "A3", "A4", "A5", "A6"]:
        pipette.transfer(1, stock[well], plate["A1"])
    pipette.transfer(1, stock["B1"], plate["A1"], mix_after=(3, 10))
    temperature.set_temperature(50)
    protocol.delay(minutes=60)
    temperature.deactivate()
