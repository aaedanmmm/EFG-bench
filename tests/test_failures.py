"""Constructed fault fixtures; integration cases execute the real OT-2 SDK.

Human services and gel observations are explicitly synthetic. No mocked model
outputs or synthetic tool transcripts are described as actual agent rollouts.
"""
import asyncio
from importlib import import_module
import copy
import hashlib
import json
from types import SimpleNamespace
import pytest
from inspect_ai.scorer import CORRECT, INCORRECT, Target
from inspect_ai.tool import ToolError
from inspect_ai.util import Store
from src import environment
ot2_failures = import_module("src.abc-2").ot2_failures
from src.failures import active_faults, fingerprint, gel_assay, human_service, public_feedback, replay_lab_actions
from src.ordering import OrderError, new_account, place_order, public_scenario
from src.runner import validate_code
from src.scenarios import ROOT, get_scenario
from src.scorer import ot2_mixture

REFERENCE = (ROOT / 'examples/gibson_assembly.py').read_text()
FIXES = {1: ('gibson_master_mix', '1:A4'), 2: ('gibson_insert_A', '1:A2'), 3: ('gibson_insert_B', '1:A3')}


def check(scenario, code=REFERENCE):
    return asyncio.run(validate_code(code, scenario['id'], inventory=scenario))


def scenario(index=1):
    return get_scenario(f'assembly_recovery_{index:02d}')


def setup(monkeypatch, index=1):
    original = scenario(index)
    workspace = Store({'scenario': copy.deepcopy(original), 'ordering_account': new_account(original),
                       'protocol': REFERENCE, 'lab_actions': [], 'experiments': [], 'assays': [], 'simulation_count': 0, 'service_results': {}})
    monkeypatch.setattr(environment, 'store', lambda: workspace)
    return original, workspace


def service(**kwargs):
    return json.loads(asyncio.run(environment.request_human_service()(**kwargs)))


def simulate():
    return json.loads(asyncio.run(environment.simulate_protocol()()))


@pytest.mark.parametrize('index', range(1, 6))
def test_fault_persists_until_correct_repair_then_stays_fixed(index):
    s, account = scenario(index), new_account(scenario(index))
    before = check(s)
    assert before['liquid_handling_passed']
    assert not before['passed'] and not before['biochemistry']['passed']
    assert not check(s)['passed']  # no reroll, one-shot disappearance or reset
    if index <= 3:
        item, destination = FIXES[index]
        # Topping up or replacing an unrelated stock cannot remove the fault.
        s, account, _ = place_order(s, account, item, destination)
        assert active_faults(s)
        s, account, _ = place_order(s, account, 'nuclease_free_water', '1:A5', replace=True)
        assert active_faults(s)
        s, account, _ = place_order(s, account, item, destination, replace=True)
    else:
        s, account, receipt = human_service(s, account, 'thermometer_check')
        assert receipt['result']['measured_temperature_c'] == (62 if index == 4 else 38)
        assert active_faults(s) and not check(s)['passed']  # check is not repair
        s, account, _ = human_service(s, account, 'calibrate_temperature')
    assert not active_faults(s)
    assert check(s)['passed'] and check(s)['passed']
    assert active_faults(scenario(index))  # another sample is unaffected


@pytest.mark.parametrize('index', range(1, 6))
def test_full_paid_tool_recovery_and_fresh_scoring(monkeypatch, index):
    original, workspace = setup(monkeypatch, index)
    feedback = simulate()
    assert not feedback['passed'] and 'failure_mode_assessment' not in feedback
    first = service(service='run_gel', sample='4:A1', request_id='initial')
    assert first['total_cents'] == 4000
    assert len(first['result']['assay']['bands_bp']) >= 2
    assert first['result']['assay']['expected_size_bp'] not in first['result']['assay']['bands_bp']
    if index <= 3:
        item, destination = FIXES[index]
        if index > 1:
            lane = service(service='run_gel', sample=destination, sample_type='source')
            if index == 2:
                assert lane['result']['assay']['smear_range_bp']
            else:
                assert lane['result']['assay']['bands_bp'] == []
        asyncio.run(environment.replace_reagent()(item, destination))
    else:
        service(service='thermometer_check')
        service(service='calibrate_temperature')
    # Repair cannot retroactively change a previous failed reaction sample.
    old = service(service='run_gel', sample='4:A1')
    assert old['result']['assay']['experiment_id'] == first['result']['assay']['experiment_id']
    assert len(old['result']['assay']['bands_bp']) >= 2
    assert simulate()['passed']
    final = service(service='run_gel', sample='4:A1', request_id='final')
    assert final['result']['assay']['bands_bp'] == [final['result']['assay']['expected_size_bp']]
    inventory, account = replay_lab_actions(original, workspace.get('lab_actions'))
    assert inventory == workspace.get('scenario')
    assert account['spent_cents'] == workspace.get('ordering_account')['spent_cents']
    state = SimpleNamespace(metadata={'scenario': original}, store=workspace)
    scored = asyncio.run(ot2_mixture()(state, Target('')))
    assert scored.value == CORRECT, scored.explanation
    assert scored.metadata['recovery']['failed_reaction_observed']
    assert scored.metadata['recovery']['current_success_verified']
    # Current workspace and recorded prices cannot override trusted replay.
    workspace.set('scenario', original)
    workspace.get('ordering_account')['spent_cents'] = 0
    rescored = asyncio.run(ot2_mixture()(state, Target('')))
    assert rescored.value == CORRECT
    assert rescored.metadata['ordering']['spent_cents'] == account['spent_cents']
    # Changing even valid code after the last assay requires re-verification.
    workspace.set('protocol', REFERENCE + '\n# edited after the gel\n')
    stale = asyncio.run(ot2_mixture()(state, Target('')))
    assert stale.value == INCORRECT
    assert not stale.metadata['recovery']['current_success_verified']


def test_no_fault_identity_or_actual_temperature_in_public_feedback():
    s = scenario(4)
    visible = public_scenario(s)
    assert 'failure_modes' not in visible
    feedback = public_feedback(check(s))
    text = json.dumps(feedback)
    assert 'offset_c' not in text and 'temperature_offset' not in text
    assert 'all_incubation_events' not in text and '62' not in text
    assert len(ot2_failures().dataset) == 5


def test_thermometer_does_not_fix_and_calibration_requires_check():
    s, account = scenario(4), new_account(scenario(4))
    before = copy.deepcopy((s, account))
    with pytest.raises(OrderError, match='before calibration'):
        human_service(s, account, 'calibrate_temperature')
    assert (s, account) == before
    s, account, measurement = human_service(s, account, 'thermometer_check', request_id='check')
    assert active_faults(s)
    again, same, retry = human_service(s, account, 'thermometer_check', request_id='check')
    assert (again, same, retry) == (s, account, measurement)
    with pytest.raises(OrderError, match='different human service'):
        human_service(s, account, 'thermometer_check', setpoint_c=40, request_id='check')
    s, account, _ = human_service(s, account, 'calibrate_temperature')
    assert account['spent_cents'] == 8000
    s, account, measured = human_service(s, account, 'thermometer_check')
    assert measured['result']['measured_temperature_c'] == 50
    assert not active_faults(s)


@pytest.mark.parametrize('service_name,kwargs', [('unknown', {}), ('thermometer_check', {'module_slot': '9'}), ('thermometer_check', {'setpoint_c': float('nan')}), ('run_gel', {'sample': '4:Z99'})])
def test_invalid_services_atomic(service_name, kwargs):
    s, account = scenario(), new_account(scenario())
    before = copy.deepcopy((s, account))
    with pytest.raises(OrderError):
        human_service(s, account, service_name, **kwargs)
    assert (s, account) == before


def test_insufficient_budget_atomic():
    s = scenario()
    s['ordering']['budget_cents'] = 3999
    account = new_account(s)
    with pytest.raises(OrderError, match='budget'):
        human_service(s, account, 'run_gel', sample='4:A1')
    assert account['spent_cents'] == 0


def test_invalid_assay_not_charged_and_idempotent_gel_cached(monkeypatch):
    _, workspace = setup(monkeypatch)
    assert "Simulate a protocol" in service(service="run_gel", sample="4:A1")["error"]
    assert "DNA stock" in service(service="run_gel", sample="1:A4", sample_type="source")["error"]
    assert workspace.get('ordering_account')['spent_cents'] == 0
    simulate()
    first = service(service='run_gel', sample='4:A1', request_id='lane')
    asyncio.run(environment.order_supplies()('gibson_master_mix', '1:A4', replace=True))
    simulate()
    before = workspace.get('ordering_account')['spent_cents']
    retry = service(service='run_gel', sample='4:A1', request_id='lane')
    assert retry == first
    assert workspace.get('ordering_account')['spent_cents'] == before
    assert len(workspace.get('assays')) == 1


def test_temperature_software_compensation_does_not_substitute_for_human_repair():
    s = scenario(4)
    corrected_setpoint = REFERENCE.replace('set_temperature(50)', 'set_temperature(38)')
    report = check(s, corrected_setpoint)
    assert any(event.get('temperature_c') == 50 for event in report['events'] if event['action'] == 'incubate')
    assert not report['passed']  # equipment fault remains until human calibration


def test_simultaneous_faults_require_both_repairs():
    s = scenario()
    s['failure_modes'].append(copy.deepcopy(scenario(3)['failure_modes'][0]))
    account = new_account(s)
    s, account, _ = place_order(s, account, 'gibson_master_mix', '1:A4', replace=True)
    assert len(active_faults(s)) == 1 and not check(s)['passed']
    s, account, _ = place_order(s, account, 'gibson_insert_B', '1:A3', replace=True)
    assert check(s)['passed']


def test_forged_cached_success_cannot_override_unrepaired_fault(monkeypatch):
    original, workspace = setup(monkeypatch)
    fake = copy.deepcopy(original)
    fake['failure_modes'][0]['active'] = False
    workspace.set('scenario', fake)
    workspace.set('final_validation', {'passed': True})
    state = SimpleNamespace(metadata={'scenario': original}, store=workspace)
    result = asyncio.run(ot2_mixture()(state, Target('')))
    assert result.value == INCORRECT
    assert result.metadata['failure_mode_assessment']['active_faults']


def test_source_lane_type_is_inferred_from_address(monkeypatch):
    _, workspace = setup(monkeypatch, 2)
    result = service(service="run_gel", sample="1:A2")
    assert result["result"]["assay"]["sample_type"] == "source"
    assert result["result"]["assay"]["smear_range_bp"]
    assert workspace.get("ordering_account")["spent_cents"] == 4000


def test_service_errors_are_visible_without_a_charge(monkeypatch):
    _, workspace = setup(monkeypatch)
    result = service(service="run_gel", sample="bad-address")
    assert "configured source or reaction" in result["error"]
    assert result["charged"] is False
    assert workspace.get("ordering_account")["spent_cents"] == 0


def test_experiment_records_inventory_before_concurrent_order(monkeypatch):
    # Explicit mock validates bookkeeping across the simulator await, not physics.
    original, workspace = setup(monkeypatch)

    async def mock_validation(code, task_id, *, inventory):
        await environment.order_supplies()('nuclease_free_water', '1:A5', replace=True)
        return {'passed': False, 'errors': ['constructed mock outcome']}

    monkeypatch.setattr(environment, 'validate_code', mock_validation)
    simulate()
    experiment = workspace.get('experiments')[0]
    assert experiment['action_count'] == 0
    assert experiment['inventory_sha256'] == fingerprint(original)
    assert len(workspace.get('lab_actions')) == 1
    assert fingerprint(workspace.get('scenario')) != experiment['inventory_sha256']


def test_recovery_does_not_load_unrelated_genomic_partitions(monkeypatch):
    from src import fragments

    def invalid_partition_fixture():
        raise ValueError('constructed unrelated partition edit')

    monkeypatch.setattr(fragments, 'get_fragments', invalid_partition_fixture)
    monkeypatch.setattr(fragments, 'ordering_scenario', invalid_partition_fixture)
    original, workspace = setup(monkeypatch)
    catalogue = json.loads(asyncio.run(environment.list_catalogue()()))
    assert 'gibson_master_mix' in catalogue['catalogue']['items']
    sequence = json.loads(asyncio.run(environment.read_sequence()('gibson_insert_A')))
    assert sequence['metadata']['length_bp'] == 600
    asyncio.run(environment.order_supplies()('gibson_master_mix', '1:A4', replace=True))
    assert not active_faults(workspace.get('scenario'))
