"""Save real public-tool observations for constructed diagnostic controls.

No model generation. Bind an Inspect sample store, call the real environment
and paid synthetic lab services, and execute protocols with the actual SDK.
No diagnostic/SDK return is mocked. A constructed repair policy is explicitly
specified here; it is not evidence that a model chose these actions.
"""
import argparse
import asyncio
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
from types import SimpleNamespace
from inspect_ai.util import Store, store
from inspect_ai.util._store import init_subtask_store
from src import environment
from src.scenarios import ROOT, load_scenarios


async def call(factory, **kwargs):
    return json.loads(await factory()(**kwargs))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'results/diagnostic_observability/observations.json')
    args = parser.parse_args()
    controls = []
    code = (ROOT/'examples/supplied_sequence_assembly.py').read_text()
    scenarios = load_scenarios('failures')
    healthy = copy.deepcopy(scenarios[0])
    healthy['failure_modes'][0]['active'] = False
    scenarios.append(healthy)
    previous = store()
    try:
        for index, scenario in enumerate(scenarios):
            workspace = Store()
            init_subtask_store(workspace)
            state = SimpleNamespace(metadata={'scenario':scenario}, store=workspace)
            await environment.initialise_environment()(state, None)
            visible = await call(environment.get_environment)
            await environment.write_protocol()(code)
            before = await call(environment.simulate_protocol)
            reaction = await call(environment.request_human_service, service='run_gel', sample='4:A1')
            lanes = [await call(environment.request_human_service, service='run_gel', sample=stock['source_well']) for stock in visible['diagnostic_reference']['dna_sources']]
            measurement = await call(environment.request_human_service, service='thermometer_check', setpoint_c=50)
            reference = visible['diagnostic_reference']
            issues = {}
            for lane in lanes:
                assay = lane['result']['assay']
                if not assay['bands_bp'] and assay['smear_range_bp'] is None:
                    issues[assay['component']] = 'no_detectable_dna'
                elif assay['smear_range_bp'] or assay['expected_size_bp'] not in assay['bands_bp']:
                    issues[assay['component']] = 'low_quality_dna'
            delta = measurement['result']['measured_temperature_c']-measurement['result']['requested_setpoint_c']
            inference = {'stock_issues':issues, 'temperature_offset_c':delta,
                         'product_band_observed':reference['expected_product_size_bp'] in reaction['result']['assay']['bands_bp']}
            entry = {'control_index':index+1, 'constructed_control':True,
                     'evaluator_only_condition':'healthy' if index==5 else scenario['failure_modes'][0]['kind'],
                     'public_environment':visible, 'public_simulation_before':before,
                     'public_reaction_gel_before':reaction, 'public_source_gels_before':lanes,
                     'public_thermometer_before':measurement,
                     'observable_only_summary':inference}
            if index < 5:
                if issues:
                    component = next(iter(issues))
                    well = next(s['source_well'] for s in reference['dna_sources'] if s['component']==component)
                    repair = await call(environment.replace_reagent, item_id=scenario['biochemistry'].get('catalogue_prefix','gibson_')+component, destination=well)
                    entry['public_repaired_source_gel'] = await call(environment.request_human_service, service='run_gel', sample=well)
                elif delta:
                    repair = await call(environment.request_human_service, service='calibrate_temperature')
                    entry['public_thermometer_after'] = await call(environment.request_human_service, service='thermometer_check', setpoint_c=50)
                else:
                    # Normal stocks + normal thermometer + failed product are
                    # consistent with enzyme inactivity, not unique biological proof.
                    repair = await call(environment.replace_reagent, item_id='gibson_master_mix', destination=next(well for well,source in scenario['sources'].items() if 'gibson_master_mix' in source['components']))
                entry['public_repair'] = repair
                entry['public_simulation_after'] = await call(environment.simulate_protocol)
                entry['public_reaction_gel_after'] = await call(environment.request_human_service, service='run_gel', sample='4:A1')
                entry['passed'] = (not before['passed'] and entry['public_simulation_after']['passed']
                    and entry['public_reaction_gel_after']['result']['assay']['bands_bp']==[reference['expected_product_size_bp']])
                if 'public_repaired_source_gel' in entry:
                    assay=entry['public_repaired_source_gel']['result']['assay']
                    entry['passed'] &= assay['bands_bp']==[assay['expected_size_bp']] and assay['smear_range_bp'] is None
                if 'public_thermometer_after' in entry:
                    entry['passed'] &= entry['public_thermometer_after']['result']['measured_temperature_c']==50
            else:
                entry['passed'] = before['passed'] and not issues and delta==0 and inference['product_band_observed']
            entry['final_spent_cents'] = workspace.get('ordering_account')['spent_cents']
            entry['sdk_commands_before'] = workspace.get('experiments')[0]['report']['opentrons_commands']
            controls.append(entry)
    finally:
        init_subtask_store(previous)
    result = {'origin':'Constructed diagnostic controls through real agent tools and SDK; not an agent/model rollout or physical observation',
              'date_utc':datetime.now(timezone.utc).isoformat(),
              'command':['python','-m','src.validate_diagnostics','--output',str(args.output)],
              'model':None,
              'dependencies':{name:importlib.metadata.version(name) for name in ('inspect-ai','opentrons','biopython')},
              'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('src/*.py','data/*.json','data/biochemistry/*.fasta','examples/supplied_sequence_assembly.py') for p in sorted(ROOT.glob(pattern))},
              'passed':all(control['passed'] for control in controls), 'controls':controls}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'controls':len(controls)}))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(asyncio.run(main()))
