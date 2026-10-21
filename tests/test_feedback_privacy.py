"""Constructed controls through real tools/SDK; no model calls or mock simulator."""
import asyncio
import copy
import json

import pytest
from inspect_ai.util import Store
from src import environment
from src.failures import public_feedback, without_incubation_details
from src.ordering import new_account
from src.runner import validate_code
from src.scenarios import ROOT, load_scenarios, get_scenario

REFERENCE = (ROOT / 'examples/supplied_sequence_assembly.py').read_text()


def test_fault_category_not_in_any_public_simulation_field(monkeypatch):
    # Use one public task identity and rotate only its hidden fault. Comparing
    # the complete tool response catches derived leaks, not only fault names.
    base = load_scenarios('failures')[0]
    before = copy.deepcopy(base)
    feedbacks = []
    private_seconds = []
    for fault_scenario in load_scenarios('failures'):
        scenario = copy.deepcopy(base)
        scenario['failure_modes'] = copy.deepcopy(fault_scenario['failure_modes'])
        workspace = Store({'scenario': scenario, 'ordering_account': new_account(scenario),
                           'protocol': REFERENCE, 'simulation_count': 0, 'lab_actions': [], 'experiments': []})
        monkeypatch.setattr(environment, 'store', lambda: workspace)
        feedback = json.loads(asyncio.run(environment.simulate_protocol()()))
        text = json.dumps(feedback)
        for forbidden in ('qualified_seconds', 'qualified_incubation_seconds', '.incubation', 'all_incubation_events', 'failure_mode_assessment', 'offset_c'):
            assert forbidden not in text
        feedbacks.append(feedback)
        report = workspace.get('last_simulation')
        private_seconds.append(report['biochemistry']['reactions'][0]['qualified_incubation_seconds'])
        assert any(check['id'].endswith('.incubation') for check in report['biochemistry']['checks'])
        assert workspace.get('experiments')[0]['report'] == report
        assert report['failure_mode_assessment']['active_faults']
    assert all(feedback == feedbacks[0] for feedback in feedbacks[1:])
    assert private_seconds == [3600, 3600, 3600, 0, 0]
    assert base == before


def test_healthy_biochemistry_tool_hides_qualifying_seconds_too(monkeypatch):
    scenario = get_scenario('sequence_assembly')
    workspace = Store({'scenario': scenario, 'ordering_account': new_account(scenario),
                       'protocol': REFERENCE, 'simulation_count': 0, 'lab_actions': []})
    monkeypatch.setattr(environment, 'store', lambda: workspace)
    feedback = json.loads(asyncio.run(environment.simulate_protocol()()))
    assert feedback['passed']
    assert 'qualified' not in json.dumps(feedback)
    assert '.incubation' not in json.dumps(feedback)
    assert workspace.get('last_simulation')['biochemistry']['reactions'][0]['qualified_incubation_seconds'] == 3600


@pytest.mark.parametrize('project', [public_feedback, without_incubation_details])
def test_projection_preserves_private_failures_and_unrelated_errors(project):
    scenario = load_scenarios('failures')[3]
    report = asyncio.run(validate_code(REFERENCE, scenario['id'], inventory=scenario))
    # Constructed unrelated error: its presence must survive privacy filtering.
    report['errors'].append('Biochemistry: 4:A1.reagent_identity')
    before = copy.deepcopy(report)
    visible = project(report)
    assert report == before
    assert not visible['passed'] and not visible['biochemistry']['passed']
    assert 'Biochemistry: 4:A1.incubation' not in visible['errors']
    assert 'Biochemistry: 4:A1.reagent_identity' in visible['errors']
    assert 'Reaction outcome failed; obtain diagnostic observations with the laboratory service tools' in visible['errors']
    assert report['biochemistry']['reactions'][0]['qualified_incubation_seconds'] == 0
