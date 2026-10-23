"""Local purchase-to-biochemistry integration check; constructed fixture, no agent.

Uses real SDK virtual hardware via the bounded protocol runtime. No purchases,
model calls, physical robot runs, or biochemical measurements are performed.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from inspect_ai.scorer import Target
from inspect_ai.util import Store
from src.ordering import new_account, place_order
from src.scenarios import ROOT, get_scenario
from src.scorer import ot2_mixture

REQUESTS=[("gibson_backbone","1:A1"),("gibson_insert_A","1:A2"),("gibson_insert_B","1:A3"),("gibson_master_mix","1:A4"),("nuclease_free_water","1:A5"),("filtered_tips_20ul","2"),("temperature_reaction_plate","4")]


async def main():
    original=get_scenario("gibson_order_supplies")
    inventory=original
    account=new_account(original)
    for item, location in REQUESTS:
        inventory,account,_=place_order(inventory,account,item,location)
    code=(ROOT / "examples/gibson_assembly.py").read_text()
    state=SimpleNamespace(metadata={"scenario":original},store=Store({"protocol":code,"ordering_account":account}))
    score=await ot2_mixture()(state,Target(""))
    report={
        "type":"Actual local integration validation using constructed order requests and protocol; not an agent rollout or experimental result",
        "command":".venv/bin/python results/archive/biochemistry_ordering/validate.py",
        "date_utc":datetime.now(timezone.utc).isoformat(),"model":None,
        "scenario_id":original["id"],"dependencies":{name:importlib.metadata.version(name) for name in ("inspect-ai","opentrons","biopython")},
        "score":score.model_dump(mode="json"),
        "source_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ("src/*.py","data/*tasks.json","data/biochemistry/*.fasta","data/ordering_catalogue.json") for p in sorted(ROOT.glob(pattern))},
    }
    destination=ROOT / "results/archive/biochemistry_ordering/validation.json"
    destination.write_text(json.dumps(report,indent=2)+"\n")
    data=score.metadata
    print(json.dumps({"passed":data["passed"],"score_breakdown":data["score_breakdown"],"biochemical_checks":len(data["biochemistry"]["checks"]),"orders":len(data["ordering"]["orders"]),"spent_cents":data["ordering"]["spent_cents"],"tips_used":data["tips_used"]},indent=2))
    return 0 if data["passed"] else 1


raise SystemExit(asyncio.run(main()))
