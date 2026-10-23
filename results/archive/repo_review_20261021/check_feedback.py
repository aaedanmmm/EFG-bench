"""Constructed reference-protocol audit of public feedback; no model calls."""
import asyncio
import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.runner import validate_code
from src.failures import public_feedback
from src.scenarios import load_scenarios


async def main():
    code = (ROOT / 'examples/supplied_sequence_assembly.py').read_text()
    outputs = []
    for scenario in load_scenarios('failures'):
        report = await validate_code(code, scenario['id'], inventory=scenario)
        feedback = public_feedback(report)
        outputs.append({
            'scenario_id': scenario['id'],
            'constructed_hidden_fault_for_audit_only': scenario['failure_modes'][0]['kind'],
            'public_errors': feedback['errors'],
            'public_incubation_checks': [c for c in feedback['biochemistry']['checks'] if c['id'].endswith('.incubation')],
            'public_qualified_incubation_seconds': [r['qualified_incubation_seconds'] for r in feedback['biochemistry']['reactions']],
        })
    result = {
        'kind': 'constructed reference-protocol audit; not a model rollout',
        'model': None,
        'python': platform.python_version(),
        'command': '.venv/bin/python results/archive/repo_review_20261021/check_feedback.py',
        'configuration': {'protocol': 'examples/supplied_sequence_assembly.py', 'scenarios': 'all five current failures tasks', 'paid_services_requested': 0},
        'outcomes': outputs,
    }
    (Path(__file__).parent / 'feedback_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
