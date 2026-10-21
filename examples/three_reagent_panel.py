"""Constructed reference protocol, not an agent rollout."""
from opentrons import protocol_api
metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    stock = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    for name, a, b, water in [("A1", 2, 3, 15), ("A2", 4, 6, 10), ("A3", 6, 9, 5)]:
        pipette.transfer(water, stock["A3"], plate[name])
        pipette.transfer(a, stock["A1"], plate[name])
        pipette.transfer(b, stock["A2"], plate[name], mix_after=(3, 10))
