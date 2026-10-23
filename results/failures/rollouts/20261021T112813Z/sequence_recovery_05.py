metadata = {
    "protocolName": "sequence_recovery_05: seven-piece circular Gibson assembly",
    "author": "OT-2 automated protocol",
    "apiLevel": "2.19",
    "description": (
        "Stitch fragment_001..fragment_006 plus the backbone source remainder into the "
        "circular benchmark target. 20 uL reaction in 4:A1: 1 uL of each of the seven "
        "overlap-ready DNA stocks (0.03 pmol each), 10 uL 2X Gibson master mix (1X final), "
        "3 uL water. Mixed 3 x 10 uL after the final addition, then incubated at 50 C for "
        "3600 s. Constructed benchmark assumptions; no experimental validation implied."
    ),
}


def run(protocol):
    # Reaction design: 20 uL total in 4:A1
    #   3 uL water + 10 uL 2X Gibson master mix (1X final)
    #   + 1 uL each of fragment_001..006 and the backbone source remainder
    # Each DNA stock is the raw data/sequences core plus the next core's first 30 bp,
    # so the seven pieces close into the 12484 bp circular product.

    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)

    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware("opentrons_96_aluminumblock_biorad_wellplate_200ul")

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    reaction = plate["A1"]

    protocol.comment("Seven-piece Gibson assembly: 20 uL reaction in well 4:A1.")

    # Aqueous components first: water, then 2X master mix
    p20.transfer(3.0, tuberack["B3"], reaction, new_tip="always")
    p20.transfer(10.0, tuberack["B2"], reaction, new_tip="always")

    # Six insert stocks, 1 uL each (fragment_001..fragment_006)
    for well in ["A1", "A2", "A3", "A4", "A5", "A6"]:
        p20.transfer(1.0, tuberack[well], reaction, new_tip="always")

    # Backbone source remainder last, with post-addition mixing (3 x 10 uL)
    p20.transfer(
        1.0,
        tuberack["B1"],
        reaction,
        new_tip="always",
        mix_after=(3, 10.0),
    )

    # Incubate at 50 C for 60 minutes, after all additions and mixing
    temp_mod.set_temperature(celsius=50)
    protocol.delay(minutes=60)
