"""Summarize saved local evidence without new model calls."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET
from inspect_ai.log import read_eval_log

root=Path(__file__).resolve().parents[2]
directory=Path(__file__).resolve().parent


def tests(name):
    cases=ET.parse(directory/name).getroot().findall('.//testcase')
    failures=[c for c in cases if c.find('failure') is not None or c.find('error') is not None]
    return {'passed':not failures,'count':len(cases),'failures_and_errors':len(failures)}


reference=json.loads((directory/'reference.json').read_text())
controls=json.loads((directory/'failure_controls.json').read_text())
diagnostics=json.loads((directory/'diagnostics.json').read_text())
prior=json.loads((root/'results/sequence_partition_validation.json').read_text())
raw_checks={piece['file']:hashlib.sha256((root/piece['file']).read_bytes()).hexdigest()==piece['sha256'] for piece in prior['pieces']}
raw_checks[prior['source']]=hashlib.sha256((root/prior['source']).read_bytes()).hexdigest()==prior['source_sha256']
check=subprocess.run(['git','diff','--check'],cwd=root,capture_output=True,text=True)
external_runs=[]
for run_path in sorted((directory/'rollouts').glob('*/run.json')):
    run_record=json.loads(run_path.read_text())
    for log_path in run_path.parent.glob('*.eval'):
        log=read_eval_log(log_path)
        samples=[]
        for sample in log.samples or []:
            scores={name:score.value for name,score in (sample.scores or {}).items()}
            samples.append({'sample_id':sample.id,'scores':scores})
        external_runs.append({'model':run_record['model'],'run_record':str(run_path.relative_to(root)),
                              'log':str(log_path.relative_to(root)),'status':log.status,'samples':samples,
                              'source_snapshot':str((run_path.parent/'source_snapshot.json').relative_to(root))})
external_status={
    'authorization':'User explicitly approved sending the seven sequence-derived inputs to OpenRouter/Kimi K3 in the current conversation.',
    'runs':external_runs,
    'status':external_runs[-1]['status'] if external_runs else 'not_started',
    'previous_attempt':'Initially rejected by automatic review before execution; authorization was then explicitly granted by the user.',
}
if (directory/'model_replay.json').exists():
    replay=json.loads((directory/'model_replay.json').read_text())
    external_status['independent_replay']={'passed':replay['passed'],'successful_recoveries':replay['successful_recoveries'],'evidence':'model_replay.json'}
judge_results=[]
for judge_path in sorted((directory/'judge').glob('*/run.json')):
    run=json.loads(judge_path.read_text())
    for sample in run['samples']:
        report_path=judge_path.parent/sample['path']
        report=json.loads(report_path.read_text())
        judge_results.append({'run_record':str(judge_path.relative_to(root)),
            'judgment':str(report_path.relative_to(root)), 'judge_model':run['judge_model'],
            'actor_model':run['actor_model'],'status':report['status'],
            'category':(report.get('assessment') or {}).get('category'),
            'refused':(report.get('assessment') or {}).get('refused'),
            'self_judgment':run['judge_model']==run['actor_model']})
record={
    'date_utc':datetime.now(timezone.utc).isoformat(), 'worktree':str(root),
    'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip(),
    'python':platform.python_version(),
    'dependencies':{name:importlib.metadata.version(name) for name in ('inspect-ai','opentrons','openai','biopython','pytest')},
    'commands':[
        '.venv/bin/python -m src.sequence_assembly --check',
        '.venv/bin/python -m src.fragments --output results/supplied_sequence_assembly/raw_manifest.json',
        '.venv/bin/python -m src.validate examples/supplied_sequence_assembly.py --scenario sequence_assembly --output results/supplied_sequence_assembly/reference.json',
        *[' '.join(r['command']) for r in (controls,diagnostics)],
        '.venv/bin/python -m pytest -q tests --junitxml=results/supplied_sequence_assembly/tests.xml',
        '.venv/bin/python -m pytest -q tests/test_supplied_assembly.py --junitxml=results/supplied_sequence_assembly/final_focused_tests.xml',
        '.venv/bin/python -m src.review examples/supplied_sequence_assembly.py --scenario sequence_assembly --output results/supplied_sequence_assembly/reference_review --origin "constructed seven-piece reference protocol; not a model rollout or physical observation"',
        '.venv/bin/python results/supplied_sequence_assembly/record_validation.py',
        'git diff --check',
    ],
    'full_tests':tests('tests.xml'), 'final_focused_tests':tests('final_focused_tests.xml'),
    'seven_piece_reference':{'passed':reference['passed'],'gate_count':len(reference['biochemistry']['checks']),'product_length_bp':len(reference['biochemistry']['assembly']['predicted_sequence']),'evidence':'reference.json'},
    'raw_fasta_unchanged_against_prior_partition_report':{'passed':all(raw_checks.values()),'checks':raw_checks,'baseline':'results/sequence_partition_validation.json'},
    'constructed_failure_controls':{'passed':controls['passed'],'count':len(controls['controls']),'evidence':'failure_controls.json'},
    'constructed_diagnostic_controls':{'passed':diagnostics['passed'],'count':len(diagnostics['controls']),'evidence':'diagnostics.json'},
    'external_model_run':external_status,
    'post_hoc_judgments':judge_results,
    'git_diff_check':{'passed':check.returncode==0,'output':check.stdout+check.stderr},
    'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ('src/*.py','tests/*.py','data/*.json','data/**/*.fasta','requirements*.txt','examples/supplied_sequence_assembly.py','docs/supplied_sequence_assembly.md','README.md') for p in sorted(root.glob(pattern))},
}
(directory/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({key:record[key] for key in ('full_tests','final_focused_tests','seven_piece_reference','constructed_failure_controls','constructed_diagnostic_controls')},indent=2))
