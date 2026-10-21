"""Diagnostic inference from public tool results, not injected fault metadata.

Stocks and assay physics are constructed. SDK execution is real. The workspace
fixture binds the same sample store that Inspect normally supplies; no simulator,
assay, thermometer, or model result is mocked.
"""
import asyncio
import copy
import json
from pathlib import Path
import pytest
from inspect_ai.util import Store
from src import environment
from src.failures import diagnostic_reference, fingerprint
from src.ordering import new_account
from src.runner import validate_code
from src.scenarios import get_scenario

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = (ROOT / 'examples/gibson_assembly.py').read_text()


def call(tool, **kwargs):
    return json.loads(asyncio.run(tool()(**kwargs)))


def workspace(monkeypatch, scenario, report=None):
    state = Store({'scenario': copy.deepcopy(scenario), 'ordering_account': new_account(scenario),
                   'protocol': REFERENCE, 'lab_actions': [], 'experiments': [], 'assays': [],
                   'simulation_count': 0, 'service_results': {}})
    monkeypatch.setattr(environment, 'store', lambda: state)
    if report is not None:
        # Actual real-SDK report from the module fixture, not a mock report.
        import hashlib
        state.set('experiments', [{'id': 'experiment-0001', 'scenario': copy.deepcopy(scenario),
            'report': copy.deepcopy(report), 'inventory_sha256': fingerprint(scenario),
            'protocol_sha256': hashlib.sha256(REFERENCE.encode()).hexdigest(), 'action_count': 0}])
    return state


def identify_stock_issues(reference, lanes):
    """Simple observable-only oracle used for validation, never agent assistance."""
    issues = {}
    for stock in reference['dna_sources']:
        lane = lanes[stock['source_well']]
        if not lane['bands_bp'] and lane['smear_range_bp'] is None:
            issues[stock['component']] = 'no_detectable_dna'
        elif lane['smear_range_bp'] or not any(abs(band-stock['expected_intact_band_bp']) <= 0.1*stock['expected_intact_band_bp'] for band in lane['bands_bp']):
            issues[stock['component']] = 'low_quality_dna'
    return issues


def source_lanes():
    reference = call(environment.get_environment)['diagnostic_reference']
    lanes = {stock['source_well']: call(environment.request_human_service, service='run_gel', sample=stock['source_well'])['result']['assay'] for stock in reference['dna_sources']}
    return reference, lanes


@pytest.mark.parametrize('kind,diagnosis', [('damaged_dna', 'low_quality_dna'), ('absent_dna', 'no_detectable_dna')])
@pytest.mark.parametrize('component,well', [('backbone','1:A1'), ('insert_A','1:A2'), ('insert_B','1:A3')])
def test_source_gels_localize_any_dna_input_using_public_sizes_only(monkeypatch, kind, diagnosis, component, well):
    scenario = get_scenario('assembly_recovery_02')
    # Rotate the fault through all inputs, so a case ID/constant well cannot pass.
    scenario['failure_modes'] = [{'kind':kind, 'component':component, 'source_well':well, 'active':True}]
    workspace(monkeypatch, scenario)
    visible = call(environment.get_environment)
    assert 'failure_modes' not in visible['scenario']
    reference, lanes = source_lanes()
    assert identify_stock_issues(reference, lanes) == {component:diagnosis}
    for stock in reference['dna_sources']:
        lane = lanes[stock['source_well']]
        assert lane['expected_size_bp'] == stock['expected_intact_band_bp']
        assert lane['component'] == stock['component']
        if stock['component'] != component:
            assert lane['bands_bp'] == [stock['expected_intact_band_bp']]
            assert lane['smear_range_bp'] is None
    # Reference does not change when the hidden fault changes or is removed.
    healthy = copy.deepcopy(scenario)
    healthy['failure_modes'] = []
    assert reference == diagnostic_reference(healthy)


@pytest.fixture(scope='module')
def real_runs():
    scenarios = [get_scenario(f'assembly_recovery_{i:02d}') for i in range(1,6)]
    healthy = copy.deepcopy(scenarios[0])
    healthy['failure_modes'][0]['active'] = False
    scenarios.append(healthy)
    return [(s, asyncio.run(validate_code(REFERENCE, s['id'], inventory=s))) for s in scenarios]


@pytest.mark.parametrize('index,expected_measurement', [(0,50), (1,50), (2,50), (3,62), (4,38), (5,50)])
def test_paid_observations_show_faulty_and_healthy_controls(monkeypatch, real_runs, index, expected_measurement):
    scenario, report = real_runs[index]
    workspace(monkeypatch, scenario, report)
    reference, lanes = source_lanes()
    reaction = call(environment.request_human_service, service='run_gel', sample='4:A1')['result']['assay']
    thermometer = call(environment.request_human_service, service='thermometer_check', setpoint_c=50)['result']
    assert thermometer['measured_temperature_c'] == expected_measurement
    issues = identify_stock_issues(reference, lanes)
    if index == 1:
        assert issues == {'insert_A':'low_quality_dna'}
    elif index == 2:
        assert issues == {'insert_B':'no_detectable_dna'}
    else:
        assert issues == {}
    assert reaction['expected_size_bp'] == reference['expected_product_size_bp'] == 2340
    if index == 5:
        assert reaction['bands_bp'] == [2340]
        assert reaction['smear_range_bp'] is None
    else:
        assert 2340 not in reaction['bands_bp']
    if index in (3,4):
        assert reaction['bands_bp'] == [600,800,1000]
        difference = thermometer['measured_temperature_c']-thermometer['requested_setpoint_c']
        assert difference > 0 if index == 3 else difference < 0
    else:
        assert thermometer['measured_temperature_c'] == thermometer['requested_setpoint_c']


def test_gel_alone_does_not_pretend_to_disambiguate_ligase_and_temperature(monkeypatch, real_runs):
    signatures = []
    for index in (0,3,4):
        scenario, report = real_runs[index]
        workspace(monkeypatch, scenario, report)
        assay = call(environment.request_human_service, service='run_gel', sample='4:A1')['result']['assay']
        signatures.append((assay['bands_bp'],assay['smear_range_bp']))
    assert signatures[0] == signatures[1] == signatures[2]
    assert 'gel alone cannot' in ' '.join(diagnostic_reference(real_runs[0][0])['diagnostic_limits']).lower()


def test_stock_replacement_and_calibration_produce_normal_diagnostics(monkeypatch, real_runs):
    for index,item,well in [(1,'gibson_insert_A','1:A2'), (2,'gibson_insert_B','1:A3')]:
        scenario, _ = real_runs[index]
        workspace(monkeypatch, scenario)
        call(environment.replace_reagent, item_id=item, destination=well)
        reference, lanes = source_lanes()
        assert identify_stock_issues(reference,lanes) == {}
    scenario, _ = real_runs[3]
    workspace(monkeypatch, scenario)
    call(environment.request_human_service, service='thermometer_check', setpoint_c=50)
    call(environment.request_human_service, service='calibrate_temperature')
    measurement = call(environment.request_human_service, service='thermometer_check', setpoint_c=50)['result']
    assert measurement['measured_temperature_c'] == measurement['requested_setpoint_c'] == 50
