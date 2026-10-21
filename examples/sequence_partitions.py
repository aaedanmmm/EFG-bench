"""Constructed liquid-handling reference using the supplied sequence identities.

This does not assemble DNA or add assembly overlaps.
"""
from opentrons import protocol_api
metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    stock = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    for name in ["A1", "A2", "A3", "A4", "A5", "A6", "B1"]:
        pipette.transfer(2, stock[name], plate["A1"])
    pipette.transfer(6, stock["B2"], plate["A1"], mix_after=(3, 10))
