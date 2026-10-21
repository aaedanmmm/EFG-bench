"""Real Opentrons virtual hardware, plus deterministic liquid accounting.

All volumes are uL. The accounting assumes ideal homogeneous liquids and
conservatively treats every dispense as tip contact. It predicts no chemistry.
"""
import copy
import math
from opentrons.simulate import get_protocol_api
from src.runtime import ProtocolError, Runtime

EPS = 1e-7


def volume(value, allow_zero=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value > 1000000 or value < (0 if allow_zero else EPS):
        raise ProtocolError("Volume must be finite and positive (uL)")
    return float(value)


def total(components):
    return sum(components.values())


class Capability:
    methods = frozenset()


class WellHandle(Capability):
    methods = frozenset()  # Use wells directly; height offsets are outside this benchmark.

    def __init__(self, robot, native, key):
        self.robot, self.native, self.key = robot, native, key


class LabwareHandle(Capability):
    methods = frozenset({"wells", "wells_by_name", "rows", "columns"})

    def __init__(self, robot, native, slot):
        self.robot, self.native, self.slot = robot, native, slot
        self.by_name = {well.well_name: WellHandle(robot, well, f"{slot}:{well.well_name}") for well in native.wells()}

    def __getitem__(self, key):
        if not isinstance(key, str):
            raise ProtocolError("Labware indexing requires a well name")
        return self.by_name[key]

    def wells(self):
        return list(self.by_name.values())

    def wells_by_name(self):
        return dict(self.by_name)

    def rows(self):
        return [[self.by_name[w.well_name] for w in row] for row in self.native.rows()]

    def columns(self):
        return [[self.by_name[w.well_name] for w in column] for column in self.native.columns()]


class Robot(Capability):
    methods = frozenset({"load_labware", "load_instrument", "load_module", "delay", "comment"})

    def __init__(self, scenario):
        self.scenario = copy.deepcopy(scenario)
        self.context = get_protocol_api(scenario["api_level"], robot_type="OT-2")
        self.labware = {}
        self.modules = {}
        self.revisions = {}
        self.pipette = None
        self.liquids = {key: dict(source["components"]) for key, source in scenario["sources"].items()}
        self.mixed = {}
        self.events = []
        self.tips_used = 0
        self.waste = {}

    def event(self, action, **data):
        if len(self.events) >= 10000:
            raise ProtocolError("Operation budget exhausted")
        self.events.append({"action": action, **data})

    def load_labware(self, load_name, location, label=None):
        slot = str(location)
        if self.scenario["labware"].get(slot) != load_name:
            raise ProtocolError(f"Labware {load_name!r} is not available in slot {slot}")
        if slot in self.scenario.get("unavailable_labware_slots", []):
            raise ProtocolError(f"Labware in slot {slot} is unavailable; order a compatible consumable first")
        if slot in self.labware:
            raise ProtocolError(f"Slot {slot} is already occupied")
        if slot in self.scenario.get("modules", {}):
            raise ProtocolError("Load this labware through its configured module")
        native = self.context.load_labware(load_name, slot, label=label)
        handle = LabwareHandle(self, native, slot)
        self.labware[slot] = handle
        for key, well in handle.by_name.items():
            initial = self.liquids.get(well.key, {})
            if total(initial) > well.native.max_volume:
                raise ProtocolError(f"Initial inventory overflows {well.key}")
        self.event("load_labware", slot=slot, load_name=load_name)
        return handle

    def load_module(self, module_name, location):
        slot = str(location)
        config = self.scenario.get("modules", {}).get(slot)
        if not config or config["model"] != module_name or slot in self.modules or slot in self.labware:
            raise ProtocolError("Use an unoccupied configured module slot and model")
        native = self.context.load_module(module_name, slot)
        handle = TemperatureModule(self, native, slot)
        self.modules[slot] = handle
        self.event("load_module", slot=slot, model=module_name)
        return handle

    def delay(self, seconds=0, minutes=0):
        seconds = volume(seconds, allow_zero=True) + 60 * volume(minutes, allow_zero=True)
        if not 0 < seconds <= 7200:
            raise ProtocolError("Delay must be positive and at most 7200 seconds")
        self.context.delay(seconds=seconds)
        for slot, module in self.modules.items():
            if module.temperature is not None:
                for well, contents in self.liquids.items():
                    if well.startswith(slot + ":") and total(contents) > EPS:
                        self.event("incubate", well=well, temperature_c=module.temperature,
                                   seconds=seconds, components_ul=dict(contents),
                                   mixed=self.mixed.get(well) == self.fingerprint(well),
                                   revision=self.revisions.get(well, 0))
        self.event("delay", seconds=seconds)

    def changed(self, key):
        self.revisions[key] = self.revisions.get(key, 0) + 1
        self.mixed.pop(key, None)

    def load_instrument(self, instrument_name, mount, tip_racks):
        config = self.scenario["pipette"]
        if self.pipette or instrument_name != config["name"] or mount != config["mount"]:
            raise ProtocolError("Use the single configured pipette and mount")
        if not isinstance(tip_racks, (list, tuple)) or not all(isinstance(rack, LabwareHandle) for rack in tip_racks):
            raise ProtocolError("tip_racks must contain loaded tip racks")
        if [rack.slot for rack in tip_racks] != config["tip_slots"]:
            raise ProtocolError("Use the specified tip racks")
        native = self.context.load_instrument(instrument_name, mount, tip_racks=[rack.native for rack in tip_racks])
        self.pipette = PipetteHandle(self, native)
        self.event("load_instrument", name=instrument_name, mount=mount)
        return self.pipette

    def comment(self, msg):
        if not isinstance(msg, str):
            raise ProtocolError("Comment must be text")
        self.context.comment(msg)

    def contents(self, well):
        if not isinstance(well, WellHandle) or well.robot is not self or well.native.parent.is_tiprack:
            raise ProtocolError("Liquid location must be a non-tiprack well in the configured deck")
        return self.liquids.setdefault(well.key, {})

    def fingerprint(self, key):
        return tuple(sorted((name, round(amount, 7)) for name, amount in self.liquids.get(key, {}).items() if amount > EPS))

    def check_final(self):
        errors = []
        tolerance = self.scenario["tolerance_ul"]
        for key, expected in self.scenario["targets"].items():
            actual = self.liquids.get(key, {})
            for component in sorted(set(actual) | set(expected)):
                if abs(actual.get(component, 0) - expected.get(component, 0)) > tolerance:
                    errors.append(f"{key}: {component} expected {expected.get(component, 0):g} uL, got {actual.get(component, 0):g}")
            if self.mixed.get(key) != self.fingerprint(key):
                errors.append(f"{key}: final mixture has not been mixed as required")
        allowed = set(self.scenario["sources"]) | set(self.scenario["targets"]) | set(self.scenario.get("waste_wells", []))
        for key, components in self.liquids.items():
            if key not in allowed and total(components) > EPS:
                errors.append(f"Unexpected liquid in {key}")
        if self.pipette and self.pipette.attached:
            errors.append("Drop the final tip before submitting")
        if self.pipette is None:
            errors.append("No pipette loaded")
        return errors


class TemperatureModule(Capability):
    methods = frozenset({"load_labware", "set_temperature", "deactivate"})

    def __init__(self, robot, native, slot):
        self.robot, self.native, self.slot = robot, native, slot
        self.temperature = None

    def load_labware(self, name):
        if self.slot in self.robot.labware or name != self.robot.scenario["modules"][self.slot]["labware"]:
            raise ProtocolError("Use the configured module labware once")
        native = self.native.load_labware(name)
        handle = LabwareHandle(self.robot, native, self.slot)
        self.robot.labware[self.slot] = handle
        self.robot.event("load_module_labware", slot=self.slot, load_name=name)
        return handle

    def set_temperature(self, celsius):
        celsius = volume(celsius)
        if not 4 <= celsius <= 95:
            raise ProtocolError("Temperature must be within 4..95 C")
        self.native.set_temperature(celsius)
        self.temperature = celsius
        self.robot.event("set_temperature", slot=self.slot, temperature_c=celsius)

    def deactivate(self):
        self.native.deactivate()
        self.temperature = None
        self.robot.event("deactivate_temperature", slot=self.slot)


class PipetteHandle(Capability):
    methods = frozenset({"pick_up_tip", "drop_tip", "aspirate", "dispense", "mix", "transfer", "blow_out"})

    def __init__(self, robot, native):
        self.robot, self.native = robot, native
        self.attached = False
        self.liquid = {}
        self.contact = set()
        self.used_tips = set()

    def check_tip(self):
        if not self.attached:
            raise ProtocolError("No tip attached")

    def check_volume(self, value):
        amount = volume(value)
        if amount < self.native.min_volume - EPS or amount > self.native.max_volume + EPS:
            raise ProtocolError(f"Volume {amount:g} outside pipette range {self.native.min_volume:g}..{self.native.max_volume:g} uL")
        return amount

    def pick_up_tip(self, location=None):
        if self.attached:
            raise ProtocolError("A tip is already attached")
        if self.robot.tips_used >= self.robot.scenario["tip_budget"]:
            raise ProtocolError("Tip budget exhausted")
        if location is not None:
            if not isinstance(location, WellHandle) or location.robot is not self.robot or location.native.parent not in self.native.tip_racks:
                raise ProtocolError("Pick up a tip from the configured tip rack")
            if location.key in self.used_tips:
                raise ProtocolError("Tip has already been used")
        # Read the same next tip the SDK will use, to reject explicit reuse too.
        selected = location.native if location else self.native.tip_racks[0].next_tip(num_tips=1)
        if selected is None:
            raise ProtocolError("Out of tips")
        rack_slot = next(slot for slot, rack in self.robot.labware.items() if rack.native is selected.parent)
        key = f"{rack_slot}:{selected.well_name}"
        available = self.robot.scenario.get("available_tips", {}).get(rack_slot, 96)
        if self.native.tip_racks[0].wells().index(selected) >= available:
            raise ProtocolError("Tip inventory exhausted; order compatible tips")
        if key in self.used_tips:
            raise ProtocolError("Tip has already been used")
        self.native.pick_up_tip(selected)
        self.used_tips.add(key)
        self.attached = True
        self.liquid, self.contact = {}, set()
        self.robot.tips_used += 1
        self.robot.event("pick_up_tip", well=key)
        return self

    def drop_tip(self):
        self.check_tip()
        self.native.drop_tip()
        for name, amount in self.liquid.items():
            self.robot.waste[name] = self.robot.waste.get(name, 0) + amount
        self.robot.event("drop_tip", discarded_components_ul=dict(self.liquid))
        self.attached = False
        self.liquid, self.contact = {}, set()
        return self

    def check_contact(self, contents):
        names = {name for name, amount in contents.items() if amount > EPS}
        if self.contact - names:
            raise ProtocolError(f"Tip carryover would contaminate this well with {sorted(self.contact - names)}; use a fresh tip")

    def aspirate(self, volume, location, rate=1.0):
        self.check_tip()
        amount = self.check_volume(volume)
        rate = globals()["volume"](rate)
        contents = self.robot.contents(location)
        source = self.robot.scenario["sources"].get(location.key, {})
        if not source.get("usable", True):
            raise ProtocolError(f"Reagent lot {source.get('lot_id', 'unknown')} in {location.key} failed quality check; order a replacement with replace=true")
        self.check_contact(contents)
        available = total(contents)
        dead = self.robot.scenario["sources"].get(location.key, {}).get("dead_volume_ul", 0)
        if available - amount < dead - EPS:
            raise ProtocolError(f"Insufficient usable liquid in {location.key}: {available:g} uL, dead volume {dead:g} uL")
        if total(self.liquid) + amount > self.native.max_volume + EPS:
            raise ProtocolError("Aspiration exceeds pipette capacity")
        if self.robot.scenario.get("require_mix_before_sampling") and location.key not in self.robot.scenario["sources"] and len([x for x in contents.values() if x > EPS]) > 1 and self.robot.mixed.get(location.key) != self.robot.fingerprint(location.key):
            raise ProtocolError(f"Mix {location.key} before sampling a dilution")
        self.native.aspirate(amount, location.native, rate=rate)
        for name in list(contents):
            moved = contents[name] * amount / available
            contents[name] -= moved
            self.liquid[name] = self.liquid.get(name, 0) + moved
        self.contact.update(name for name, qty in self.liquid.items() if qty > EPS)
        self.robot.changed(location.key)
        self.robot.event("aspirate", well=location.key, volume_ul=amount)
        return self

    def dispense(self, volume, location, rate=1.0):
        self.check_tip()
        amount = self.check_volume(volume)
        rate = globals()["volume"](rate)
        contents = self.robot.contents(location)
        held = total(self.liquid)
        if amount > held + EPS:
            raise ProtocolError("Dispense exceeds liquid held in the tip")
        if total(contents) + amount > location.native.max_volume + EPS:
            raise ProtocolError(f"Well overflow in {location.key}")
        if location.key in self.robot.scenario["sources"]:
            self.check_contact(contents)
        self.native.dispense(amount, location.native, rate=rate)
        self.deposit(contents, amount, held)
        self.contact.update(name for name, qty in contents.items() if qty > EPS)
        self.robot.changed(location.key)
        self.robot.event("dispense", well=location.key, volume_ul=amount)
        return self

    def deposit(self, contents, amount, held):
        if held <= EPS:
            return
        for name in list(self.liquid):
            moved = self.liquid[name] * amount / held
            self.liquid[name] -= moved
            contents[name] = contents.get(name, 0) + moved

    def blow_out(self, location):
        self.check_tip()
        contents = self.robot.contents(location)
        amount = total(self.liquid)
        if total(contents) + amount > location.native.max_volume + EPS:
            raise ProtocolError(f"Well overflow in {location.key}")
        if location.key in self.robot.scenario["sources"]:
            self.check_contact(contents)
        self.native.blow_out(location.native)
        self.deposit(contents, amount, amount)
        self.contact.update(name for name, qty in contents.items() if qty > EPS)
        if amount > EPS:
            self.robot.changed(location.key)
        self.robot.event("blow_out", well=location.key, volume_ul=amount)
        return self

    def mix(self, repetitions, volume, location, rate=1.0):
        self.check_tip()
        amount = self.check_volume(volume)
        rate = globals()["volume"](rate)
        if type(repetitions) is not int or repetitions < 1 or repetitions > 100:
            raise ProtocolError("Mix repetitions must be an integer from 1 to 100")
        if total(self.liquid) > EPS:
            raise ProtocolError("Empty the tip before mixing")
        contents = self.robot.contents(location)
        self.check_contact(contents)
        dead = self.robot.scenario["sources"].get(location.key, {}).get("dead_volume_ul", 0)
        if amount > total(contents) - dead + EPS:
            raise ProtocolError("Mix volume exceeds usable liquid")
        self.native.mix(repetitions, amount, location.native, rate=rate)
        self.contact.update(name for name, qty in contents.items() if qty > EPS)
        required = self.robot.scenario["mix"]
        if repetitions >= required["repetitions"] and amount >= required["volume_ul"] - EPS:
            self.robot.mixed[location.key] = self.robot.fingerprint(location.key)
        self.robot.event("mix", well=location.key, repetitions=repetitions, volume_ul=amount)
        return self

    def transfer(self, volume, source, dest, new_tip="always", mix_after=None):
        # A deliberately narrow, documented version of the SDK complex command.
        amount = globals()["volume"](volume)
        if amount > 200:
            raise ProtocolError("One transfer is limited to 200 uL")
        if new_tip not in ("always", "never"):
            raise ProtocolError("Supported transfer new_tip values: 'always', 'never'")
        if not isinstance(source, WellHandle) or not isinstance(dest, WellHandle):
            raise ProtocolError("Transfer requires one source well and one destination well; use a loop for lists")
        if new_tip == "always":
            self.pick_up_tip()
        self.check_tip()
        if total(self.liquid) > EPS:
            raise ProtocolError("Transfer requires an empty tip")
        # Equal chunks avoid a final aliquot smaller than the pipette minimum.
        chunks = math.ceil(amount / self.native.max_volume)
        for _ in range(chunks):
            self.aspirate(amount / chunks, source)
            self.dispense(amount / chunks, dest)
        if mix_after is not None:
            if not isinstance(mix_after, (tuple, list)) or len(mix_after) != 2:
                raise ProtocolError("mix_after must be (repetitions, volume)")
            self.mix(mix_after[0], mix_after[1], dest)
        if new_tip == "always":
            self.drop_tip()
        return self


def simulate_protocol(code, scenario):
    """Interpret a protocol using real SDK virtual hardware; return JSON evidence."""
    robot = None
    errors = []
    try:
        robot = Robot(scenario)
        Runtime(robot).run(code)
        errors.extend(robot.check_final())
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    report = {
        "passed": not errors,
        "liquid_handling_passed": not errors,
        "well_revisions": dict(robot.revisions) if robot else {},
        "scenario_id": scenario["id"],
        "engine": "opentrons virtual hardware + bounded Python interpreter + ideal liquid ledger",
        "errors": errors,
        "tips_used": robot.tips_used if robot else 0,
        "tip_budget": scenario["tip_budget"],
        "final_wells": {key: {name: round(qty, 8) for name, qty in contents.items() if qty > EPS} for key, contents in (robot.liquids.items() if robot else [])},
        "discarded_components_ul": robot.waste if robot else {},
        "events": robot.events if robot else [],
        "opentrons_commands": list(robot.context.commands()) if robot else [],
    }

    from src.biochemistry import evaluate_biochemistry
    report["biochemistry"] = evaluate_biochemistry(scenario, report)
    if report["biochemistry"]["applicable"] and not report["biochemistry"]["passed"]:
        report["passed"] = False
        report["errors"].extend("Biochemistry: " + check["id"] for check in report["biochemistry"]["checks"] if not check["passed"])
    return report
