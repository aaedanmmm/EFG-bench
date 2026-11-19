"""Independently replay actual Inspect fault-recovery artifacts and history."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from inspect_ai.log import read_eval_log
from inspect_ai.scorer import CORRECT, Target
from inspect_ai.util import Store
from src.failures import fingerprint, gel_assay, replay_lab_actions
from src.observations import enabled as ambiguous_enabled
from src.runner import validate_code
from src.scenarios import ROOT
from src.scorer import ot2_mixture


def replay_observations(original, actions, experiments, assays, recorded_account):
    """Recompute every paid observation, including source checks and thermometers."""
    checks = []
    for assay in assays:
        try:
            count = assay["action_count"]
            if type(count) is not int or not 1 <= count <= len(actions):
                raise ValueError("Invalid action count")
            action = actions[count - 1]
            inventory, account = replay_lab_actions(original, actions[:count])
            receipt = account["human_services"][-1]
            request = receipt["request"]
            if (action["kind"] != "human_service" or request["service"] != "run_gel"
                    or receipt["service_id"] != assay["service_id"]):
                raise ValueError("Assay is not bound to its paid service")
            experiment = next((e for e in experiments if e["id"] == assay.get("experiment_id")), None)
            expected = gel_assay(inventory, request["sample"], request["sample_type"],
                                 experiment=experiment, measurement_id=receipt["service_id"])
            expected.update(service_id=receipt["service_id"], action_count=count)
            checks.append({"service_id": receipt["service_id"], "matched": expected == assay})
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            checks.append({"service_id": assay.get("service_id"), "matched": False, "error": str(exc)})
    _, account = replay_lab_actions(original, actions)
    # Thermometer findings are generated during action replay. Gel assays are
    # attached by the environment and checked independently above.
    recorded_services = (recorded_account or {}).get("human_services", [])
    service_checks = []
    for receipt in account.get("human_services", []):
        saved = next((r for r in recorded_services if r["service_id"] == receipt["service_id"]), None)
        if receipt["request"]["service"] != "run_gel":
            service_checks.append({"service_id": receipt["service_id"], "matched": saved == receipt})
    return {"assays": checks, "other_services": service_checks,
            "all_matched": all(check["matched"] for check in checks + service_checks)}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('--output', type=Path, default=Path('results/failures/replay.json'))
    args = parser.parse_args()
    log = read_eval_log(args.log)
    samples = []
    for sample in log.samples or []:
        original = sample.metadata['scenario']
        if not original.get('failure_modes') or not sample.scores:
            continue
        codes = {}
        for message in sample.messages:
            for call in getattr(message, 'tool_calls', None) or []:
                if call.function == 'write_protocol' and isinstance(call.arguments.get('code'), str):
                    code = call.arguments['code']
                    codes[hashlib.sha256(code.encode()).hexdigest()] = code
        state = SimpleNamespace(metadata=sample.metadata, store=Store(sample.store))
        actions = state.store.get('lab_actions', [])
        timeline = []
        for experiment in state.store.get('experiments', []):
            inventory, _ = replay_lab_actions(original, actions[:experiment['action_count']])
            source = codes.get(experiment['protocol_sha256'])
            if source is None:
                timeline.append({'experiment_id':experiment['id'], 'matched':False, 'error':'No matching write_protocol call'})
                continue
            fresh = await validate_code(source, original['id'], inventory=inventory)
            same = (fingerprint(inventory) == experiment['inventory_sha256']
                    and fresh['passed'] == experiment['report']['passed']
                    and fresh.get('liquid_handling_passed') == experiment['report'].get('liquid_handling_passed')
                    and fresh.get('failure_mode_assessment') == experiment['report'].get('failure_mode_assessment'))
            timeline.append({'experiment_id':experiment['id'], 'matched':same, 'replay':fresh})
        rescored = await ot2_mixture()(state, Target(''))
        recorded = next(iter(sample.scores.values()))
        result = {'sample_id':sample.id, 'original_score':recorded.value, 'replayed_score':rescored.value,
                        'score_matched':recorded.value == rescored.value,
                        'all_experiments_matched':all(e['matched'] for e in timeline),
                        'experiments':timeline, 'final_score_evidence':rescored.metadata}
        if ambiguous_enabled(original):
            result['observations'] = replay_observations(original, actions, state.store.get('experiments', []),
                                                         state.store.get('assays', []), state.store.get('ordering_account'))
            result['calibration_matched'] = (recorded.metadata or {}).get('calibration') == (rescored.metadata or {}).get('calibration')
        samples.append(result)
    result = {'origin':'Independent replay of actual model artifacts and tool-owned experiment history; no new model generation',
              'date_utc':datetime.now(timezone.utc).isoformat(), 'model':log.eval.model,
              'command':['python','-m','src.replay_failures',str(args.log),'--output',str(args.output)],
              'log_status':log.status, 'log_sha256':hashlib.sha256(args.log.read_bytes()).hexdigest(),
              'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('src/*.py','data/*.json') for p in sorted(ROOT.glob(pattern))},
              'passed':bool(samples) and all(s['score_matched'] and s['all_experiments_matched']
                                             and s.get('observations', {}).get('all_matched', True)
                                             and s.get('calibration_matched', True) for s in samples),
              'successful_recoveries':sum(s['replayed_score'] == CORRECT for s in samples), 'samples':samples}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('passed','successful_recoveries')}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
