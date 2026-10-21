"""Record the assessment's actual saved checks; no model calls or code execution."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent


def test_summary(path):
    cases = ET.parse(path).getroot().findall('.//testcase')
    suites = {}
    for case in cases:
        outcome = 'failed' if case.find('failure') is not None else 'error' if case.find('error') is not None else 'passed'
        counts = suites.setdefault(case.get('classname'), Counter())
        counts[outcome] += 1
    totals = sum((counts for counts in suites.values()), Counter())
    return {'total':len(cases), **dict(totals), 'suites':{name:dict(counts) for name,counts in suites.items()},
            'all_failure_messages_include_partition_length_error':all('Expected a 1000 bp partition' in (issue.text or '') for case in cases for issue in (case.find('failure'),case.find('error')) if issue is not None)}


controls = json.loads((directory/'controls.json').read_text())
strict = json.loads((directory/'replay.json').read_text())
behavior = json.loads((directory/'behavioral_replay.json').read_text())
static_tasks = {p.name:json.loads(p.read_text()) for p in root.glob('data/*_tasks.json')}
removed = not any(task['id'] == 'replace_failed_lot' or 'faulty_lots' in task.get('ordering', {}) for tasks in static_tasks.values() for task in tasks)
source_paths = [p for pattern in ('src/*.py','tests/*.py','data/*.json','data/**/*.fasta','requirements*.txt','docs/failure_modes.md','README.md','results/failure_system_review/*.py') for p in root.glob(pattern)]
check = subprocess.run(['git','diff','--check'],cwd=root,text=True,capture_output=True)
record = {
    'date_utc':datetime.now(timezone.utc).isoformat(),
    'worktree':str(root), 'branch':subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip(),
    'python':platform.python_version(),
    'dependencies':{name:importlib.metadata.version(name) for name in ('inspect-ai','opentrons','openai','biopython','pytest')},
    'commands':[
        '.venv/bin/python -m pytest -q tests --junitxml=results/failure_system_review/tests.xml',
        '.venv/bin/python -m pytest -q tests/test_failures.py --junitxml=results/failure_system_review/recovery_tests.xml',
        *[' '.join(command) for command in (controls['command'],strict['command'],behavior['command'])],
        '.venv/bin/python results/failure_system_review/record_validation.py',
        'git diff --check',
    ],
    'retired_task_and_schedules_absent_from_active_data':removed,
    'full_tests':test_summary(directory/'tests.xml'),
    'post_rename_recovery_tests':test_summary(directory/'recovery_tests.xml'),
    'constructed_fault_controls':{'passed':controls['passed'],'count':len(controls['controls']),'evidence':'controls.json','not_model_rollouts':True},
    'historical_model':'openrouter/moonshotai/kimi-k3',
    'new_model_calls':0,
    'strict_archived_replay':{'passed':strict['passed'],'evidence':'replay.json','reason':'Historical post-order inventory hashes include the removed usable=true field'},
    'archived_behavior_comparison':{'passed':behavior['passed'],'samples':len(behavior['samples']),'evidence':'behavioral_replay.json','not_an_exact_replay_or_new_rollout':True},
    'git_diff_check':{'passed':check.returncode==0,'output':check.stdout+check.stderr},
    'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(source_paths))},
    'assessment':'Legacy failed-lot mechanism removed. All five current fault controls pass. Global benchmark remains blocked by unrelated sequence/catalogue validation. Successful model evidence covers ligase only.',
}
(directory/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({key:record[key] for key in ('retired_task_and_schedules_absent_from_active_data','post_rename_recovery_tests','constructed_fault_controls','strict_archived_replay','archived_behavior_comparison')},indent=2))
