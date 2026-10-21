"""Constructed reference protocol, not an agent rollout or wet-lab validation."""
from opentrons import protocol_api

metadata = {"apiLevel": "2.19", "protocolName": "Synthetic two-reagent mixture"}


def run(protocol: protocol_api.ProtocolContext):
    stock = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    for name in ["A1", "A2"]:
        pipette.transfer(15, stock["A2"], plate[name])
        pipette.transfer(5, stock["A1"], plate[name], mix_after=(3, 10))
