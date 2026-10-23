"""Constructed reference protocol, not an agent rollout."""
from opentrons import protocol_api
metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    stock = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "1")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    pipette = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    for name in ["A1", "A2", "A3"]:
        pipette.transfer(20, stock["A2"], plate[name])
    pipette.transfer(20, stock["A1"], plate["A1"])
    pipette.pick_up_tip()
    pipette.mix(3, 10, plate["A1"])
    pipette.drop_tip()
    pipette.transfer(20, plate["A1"], plate["A2"], mix_after=(3, 10))
    pipette.transfer(20, plate["A2"], plate["A3"], mix_after=(3, 10))
    pipette.transfer(20, plate["A3"], plate["A12"])
    for name in ["A1", "A2", "A3"]:
        pipette.pick_up_tip()
        pipette.mix(3, 10, plate[name])
        pipette.drop_tip()
