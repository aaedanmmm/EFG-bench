"""Save constructed before/after fault controls using the real SDK runtime.

These are deterministic integration controls, not model-generated rollouts.
"""
import argparse
import asyncio
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
from src.failures import active_faults, fingerprint, gel_assay, human_service, replay_lab_actions
from src.ordering import new_account, place_order
from src.runner import validate_code
from src.scenarios import ROOT, load_scenarios


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/failures/controls.json')
    args = parser.parse_args()
    code = (ROOT / 'examples/supplied_sequence_assembly.py').read_text()
    controls = []
    for original in load_scenarios('failures'):
        scenario, account = copy.deepcopy(original), new_account(original)
        first = await validate_code(code, scenario['id'], inventory=scenario)
        repeated = await validate_code(code, scenario['id'], inventory=scenario)
        experiment = {'id': 'constructed-before', 'scenario': copy.deepcopy(scenario), 'report': first,
                      'protocol_sha256': hashlib.sha256(code.encode()).hexdigest(), 'inventory_sha256': fingerprint(scenario)}
        scenario, account, diagnostic = human_service(scenario, account, 'run_gel', sample='4:A1')
        actions = [{'kind': 'human_service', 'request': diagnostic['request']}]
        before_gel = gel_assay(scenario, '4:A1', 'reaction', experiment=experiment)
        fault = active_faults(scenario)[0]
        source_gel = None
        if fault['kind'] == 'temperature_offset':
            scenario, account, thermometer = human_service(scenario, account, 'thermometer_check')
            actions.append({'kind': 'human_service', 'request': thermometer['request']})
            scenario, account, repair = human_service(scenario, account, 'calibrate_temperature')
            actions.append({'kind': 'human_service', 'request': repair['request']})
        else:
            thermometer = None
            if fault['kind'] in ('damaged_dna', 'absent_dna'):
                scenario, account, lane = human_service(scenario, account, 'run_gel', sample=fault['source_well'], sample_type='source')
                actions.append({'kind': 'human_service', 'request': lane['request']})
                source_gel = gel_assay(scenario, fault['source_well'], 'source')
            component = fault['component']
            item = 'gibson_master_mix' if component == 'gibson_master_mix' else scenario['biochemistry'].get('catalogue_prefix', 'gibson_') + component
            scenario, account, repair = place_order(scenario, account, item, fault['source_well'], replace=True)
            actions.append({'kind': 'order', 'request': repair['request']})
        old_gel_after_repair = gel_assay(scenario, '4:A1', 'reaction', experiment=experiment)
        after = await validate_code(code, scenario['id'], inventory=scenario)
        again = await validate_code(code, scenario['id'], inventory=scenario)
        final_experiment = {'id': 'constructed-after', 'scenario': copy.deepcopy(scenario), 'report': after,
                            'protocol_sha256': experiment['protocol_sha256'], 'inventory_sha256': fingerprint(scenario)}
        scenario, account, final_receipt = human_service(scenario, account, 'run_gel', sample='4:A1')
        actions.append({'kind': 'human_service', 'request': final_receipt['request']})
        after_gel = gel_assay(scenario, '4:A1', 'reaction', experiment=final_experiment)
        rebuilt, charged = replay_lab_actions(original, actions)
        passed = (not first['passed'] and first['liquid_handling_passed'] and not repeated['passed']
                  and after['passed'] and again['passed'] and before_gel == old_gel_after_repair
                  and after_gel['bands_bp'] == [after_gel['expected_size_bp']]
                  and rebuilt == scenario and charged['spent_cents'] == account['spent_cents'])
        controls.append({'scenario_id': original['id'], 'constructed_control': True, 'fault': original['failure_modes'],
                         'passed': passed, 'before': first, 'repeat_before': repeated, 'before_gel': before_gel,
                         'source_gel': source_gel, 'thermometer': thermometer, 'repair_receipt': repair,
                         'old_sample_after_repair': old_gel_after_repair, 'after': after, 'repeat_after': again,
                         'after_gel': after_gel, 'actions': actions, 'total_cents': charged['spent_cents']})
    record = {'constructed': True, 'origin': 'Deterministic integration controls; not an agent rollout or experimental observation',
              'date_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
              'opentrons': importlib.metadata.version('opentrons'),
              'command': ['python', '-m', 'src.validate_failures', '--output', args.output],
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('src/*.py','data/*.json','examples/supplied_sequence_assembly.py') for p in sorted(ROOT.glob(pattern))},
              'passed': all(c['passed'] for c in controls), 'controls': controls}
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'passed': record['passed'], 'constructed_controls':len(controls)}))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
