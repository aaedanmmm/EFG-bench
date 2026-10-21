"""Compare archived model behavior under current semantics after lot-field removal.

This supplements strict replay.json; it does not rewrite old logs or hashes and
must not be described as an exact history replay or a new model rollout.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from inspect_ai.log import read_eval_log
from src.failures import fingerprint, gel_assay, replay_lab_actions
from src.runner import validate_code


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    log = read_eval_log(args.log)
    records = []
    for sample in log.samples or []:
        original = sample.metadata['scenario']
        store = sample.store
        if not original.get('failure_modes') or not sample.scores:
            continue
        actions = store['lab_actions']
        codes = {hashlib.sha256(call.arguments['code'].encode()).hexdigest(): call.arguments['code']
                 for message in sample.messages for call in getattr(message, 'tool_calls', None) or []
                 if call.function == 'write_protocol' and isinstance(call.arguments.get('code'), str)}
        experiments = []
        fresh_experiments = {}
        for experiment in store['experiments']:
            inventory, _ = replay_lab_actions(original, actions[:experiment['action_count']])
            fresh = await validate_code(codes[experiment['protocol_sha256']], original['id'], inventory=inventory)
            old = experiment['report']
            checks = {key: fresh.get(key) == old.get(key) for key in ('passed', 'liquid_handling_passed', 'failure_mode_assessment', 'final_wells', 'tips_used')}
            checks['biochemistry_passed'] = fresh['biochemistry']['passed'] == old['biochemistry']['passed']
            # Identify the inventory drift without modifying saved inventory or hashes.
            old_inventory = json.loads(json.dumps(experiment['scenario']))
            for source in old_inventory['sources'].values():
                if 'usable' in source:
                    if source['usable'] is not True:
                        raise ValueError('Cannot treat a legacy unusable stock as equivalent')
                    del source['usable']
            equals_without_retired_flags = inventory == old_inventory
            fresh_experiments[experiment['id']] = {**experiment, 'scenario': inventory, 'report': fresh, 'inventory_sha256': fingerprint(inventory)}
            experiments.append({'experiment_id':experiment['id'], 'behavior_checks':checks,
                                'behavior_matched':all(checks.values()),
                                'exact_inventory_hash_matched':fingerprint(inventory) == experiment['inventory_sha256'],
                                'inventory_equal_after_removing_retired_usable_true_fields':equals_without_retired_flags})
        gels = []
        for assay in store['assays']:
            if assay['sample_type'] != 'reaction':
                continue
            experiment = fresh_experiments[assay['experiment_id']]
            current = gel_assay(experiment['scenario'], assay['sample'], 'reaction', experiment=experiment)
            # Inventory hashes intentionally differ; compare every other public observation.
            fields = {key: current[key] == assay.get(key) for key in current if key != 'inventory_sha256'}
            gels.append({'experiment_id':assay['experiment_id'], 'observation_checks':fields, 'observations_matched':all(fields.values())})
        inventory, account = replay_lab_actions(original, actions)
        final = await validate_code(store['protocol'], original['id'], inventory=inventory)
        score = next(iter(sample.scores.values()))
        records.append({'sample_id':sample.id, 'archived_score':score.value,
                        'current_final_protocol_passed':final['passed'], 'current_cost_cents':account['spent_cents'],
                        'recorded_cost_cents':score.metadata['ordering']['spent_cents'],
                        'experiments':experiments, 'gels':gels,
                        'behavioral_match':all(e['behavior_matched'] and e['inventory_equal_after_removing_retired_usable_true_fields'] for e in experiments)
                                           and all(g['observations_matched'] for g in gels)
                                           and final['passed'] and account['spent_cents'] == score.metadata['ordering']['spent_cents']})
    record = {'origin':'Behavior comparison of real archived Kimi artifacts using the current bounded interpreter; no new model generation and no changes to archived hashes',
              'date_utc':datetime.now(timezone.utc).isoformat(), 'model':log.eval.model,
              'command':['python','results/archive/failure_system_review/assess_replay.py',str(args.log),'--output',str(args.output)],
              'log_sha256':hashlib.sha256(args.log.read_bytes()).hexdigest(),
              'passed':bool(records) and all(r['behavioral_match'] for r in records), 'samples':records,
              'limitation':'Strict replay remains incompatible with historical post-order inventory hashes because removed usable=true fields contributed to those hashes; see replay.json'}
    args.output.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'behavioral_match':record['passed'], 'samples':len(records)}))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
