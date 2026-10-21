"""Live model checks of hand-constructed rubric cases, never actual agent rollouts."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.judge import DEFAULT_JUDGE_MODEL, RUBRIC, assess_timeline


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path)
    parser.add_argument('--model',default=DEFAULT_JUDGE_MODEL)
    parser.add_argument('--fixtures',type=Path,default=Path('tests/fixtures/judge_cases.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    if not os.environ.get('OPENROUTER_API_KEY') and os.environ.get('OPEN-ROUTER_API'):
        os.environ['OPENROUTER_API_KEY']=os.environ['OPEN-ROUTER_API']
    path=args.fixtures
    cases=json.loads(path.read_text())['cases']
    record={'origin':'Live model judgments of constructed calibration transcripts, NOT actual actor rollouts','model':args.model,
            'started_at_utc':datetime.now(timezone.utc).isoformat(),'rubric':RUBRIC,
            'fixture_path':str(path),'fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'command':['python','results/judge/check_calibration.py','--model',args.model,'--fixtures',str(args.fixtures),'--output',str(args.output)],'cases':[]}
    for case in cases:
        report=await assess_timeline(case['events'],model=args.model)
        assessment=report.get('assessment') or {}
        matched=report['status'] in case.get('expected_statuses', [case['expected_status']]) and assessment.get('category')==case['expected_category']
        for key in ('refused', 'refusal_scope'):
            if 'expected_' + key in case:
                matched = matched and assessment.get(key) == case['expected_' + key]
        record['cases'].append({'id':case['id'],'expected_category':case['expected_category'],'expected_status':case['expected_status'],'expected_statuses':case.get('expected_statuses', [case['expected_status']]),'expected_refused':case.get('expected_refused'),'expected_refusal_scope':case.get('expected_refusal_scope'),'matched':matched,'report':report})
        args.output.write_text(json.dumps(record,indent=2)+'\n')
        print(case['id'],report['status'],assessment.get('category'),assessment.get('refused'),matched,flush=True)
    record['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    record['matched']=sum(c['matched'] for c in record['cases'])
    record['total']=len(cases)
    args.output.write_text(json.dumps(record,indent=2)+'\n')
    return 0 if record['matched']==record['total'] else 1


raise SystemExit(asyncio.run(main()))
