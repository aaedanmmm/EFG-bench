metadata = {
    "protocolName": "sequence_recovery_03: seven-piece Gibson assembly",
    "author": "OT-2 automated protocol",
    "description": (
        "Assemble fragment_001..fragment_006 plus the named backbone remainder "
        "into the circular benchmark target (20 uL, 1X master mix, 50 C, 60 min)."
    ),
    "apiLevel": "2.19",
}

# ---------------------------------------------------------------------------
# Deck layout (from the task environment)
#   slot 1 : opentrons_24_tuberack_nest_1.5ml_snapcap  (reagent stocks)
#   slot 2 : opentrons_96_tiprack_20ul                 (tips, budget 12)
#   slot 4 : temperature module gen2 + opentrons_96_aluminumblock_biorad_wellplate_200ul
# ---------------------------------------------------------------------------

# Reagent source wells
FRAGMENT_WELLS = ["A1", "A2", "A3", "A4", "A5", "A6"]  # fragment_001..006
BACKBONE_WELL = "B1"                                   # backbone (source remainder)
MASTER_MIX_WELL = "B2"                                 # 2X gibson master mix
WATER_WELL = "B3"                                      # nuclease-free water

# Reaction well on the temperature module plate
DEST_WELL = "A1"

# Target mixture (uL) -> 3 water + 10 master mix + 7 x 1 DNA = 20 uL
WATER_UL = 3.0
MASTER_MIX_UL = 10.0
DNA_UL = 1.0

MIX_REPETITIONS = 3
MIX_VOLUME_UL = 10.0

INCUBATION_C = 50
INCUBATION_SECONDS = 3600


def run(protocol):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)

    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware(
        "opentrons_96_aluminumblock_biorad_wellplate_200ul"
    )

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    dest = plate[DEST_WELL]

    # Build the ordered addition list: water, master mix, then each DNA piece.
    additions = [
        (WATER_UL, tuberack[WATER_WELL], "water"),
        (MASTER_MIX_UL, tuberack[MASTER_MIX_WELL], "gibson_master_mix (2X)"),
    ]
    for well in FRAGMENT_WELLS:
        additions.append((DNA_UL, tuberack[well], "fragment DNA"))
    additions.append((DNA_UL, tuberack[BACKBONE_WELL], "backbone DNA"))

    # --- Assemble the 20 uL reaction at ambient temperature -----------------
    for volume, source, label in additions:
        p20.pick_up_tip()
        p20.aspirate(volume, source)
        p20.dispense(volume, dest)
        p20.blow_out(dest)
        p20.drop_tip()

    # --- Mix the complete reaction (3 x 10 uL) ------------------------------
    p20.pick_up_tip()
    p20.mix(MIX_REPETITIONS, MIX_VOLUME_UL, dest)
    p20.drop_tip()

    protocol.comment(
        "Reaction 4:A1 assembled: 3 uL water + 10 uL 2X master mix + "
        "7 x 1 uL DNA (0.03 pmol each) = 20 uL, 1X master mix."
    )

    # --- Incubate at 50 C for 60 min (heating follows final additions) ------
    temp_mod.set_temperature(INCUBATION_C)
    protocol.delay(seconds=INCUBATION_SECONDS)

    protocol.comment("Incubation complete: 50 C for 3600 s.")
