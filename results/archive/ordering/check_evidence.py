"""Summarise completed synthetic rollouts and local sequence validation; no APIs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from dotenv import dotenv_values
from inspect_ai.log import read_eval_log
from src.fragments import sequence_manifest, read_fasta
from src.scenarios import ROOT

run_directory = ROOT / "results/archive/ordering/rollouts/20261021T072202Z"
record = json.loads((run_directory / "run.json").read_text())
log = read_eval_log(next(run_directory.glob("*.eval")))
if log.status != "success":
    raise RuntimeError(f"Rollout has not successfully finished: {log.status}")
manifest = sequence_manifest()
sequences = [read_fasta(ROOT / item["sequence_file"])[1] for item in manifest["fragments"].values()]
sequence_hashes = [item[key] for item in manifest["fragments"].values() for key in ("sha256","file_sha256")]
model_messages = "\n".join(message.model_dump_json() for sample in log.samples or [] for message in sample.messages)
sequence_transfer_detected = any(value in model_messages for value in sequences + sequence_hashes)
assert not sequence_transfer_detected, "Supplied sequence data appeared in synthetic task messages"
secret_values = [v for v in dotenv_values(ROOT.parent / "MATS-work-test/.env").values() if v and len(v)>=8]
secret_hits = []
for directory in (ROOT / "results/archive/ordering", ROOT / "results/archive/sequences"):
    for path in directory.rglob("*"):
        if path.is_file():
            content = read_eval_log(path).model_dump_json() if path.suffix == ".eval" else path.read_text(errors="replace")
            if any(value in content for value in secret_values):
                secret_hits.append(str(path.relative_to(ROOT)))
assert not secret_hits, f"Credential-containing evidence files: {secret_hits}"
root = ET.parse(ROOT / "results/archive/ordering/tests.xml").getroot()
tests = sum(int(s.attrib.get("tests",0)) for s in root.findall("testsuite"))
failures = sum(int(s.attrib.get("failures",0))+int(s.attrib.get("errors",0)) for s in root.findall("testsuite"))
samples = []
for sample in log.samples or []:
    for score in (sample.scores or {}).values():
        account=(score.metadata or {}).get("ordering",{})
        samples.append({"id":sample.id,"score":score.value,"spent_cents":account.get("spent_cents"),"remaining_cents":account.get("remaining_cents"),"orders":len(account.get("orders",[])),"simulations":(score.metadata or {}).get("simulation_count")})
local=json.loads((ROOT / "results/archive/sequences/integration.json").read_text())
summary={
    "date_utc":datetime.now(timezone.utc).isoformat(),
    "command":".venv/bin/python results/archive/ordering/check_evidence.py",
    "rollout_command":".venv/bin/python -m src.run_eval --env-file ../MATS-work-test/.env --suite ordering --limit 2 --message-limit 60 --output results/archive/ordering/rollouts",
    "model":record["model"],"configuration":record["configuration"],"dependencies":record["dependencies"],
    "rollout":str(run_directory.relative_to(ROOT)),"status":log.status,"samples":samples,
    "tests":{"total":tests,"failures_and_errors":failures,"evidence":["results/archive/ordering/tests.txt","results/archive/ordering/tests.xml"]},
    "local_sequence_integration":{"passed":local["passed"],"source_bp":manifest["source"]["length_bp"],"part_count":len(manifest["fragments"]),"input_bytes_preserved":local["input_fasta_bytes_preserved"],"evidence":"results/archive/sequences/integration.json","is_model_rollout":False},
    "supplied_sequence_external_rollout":"not run; approval pending",
    "synthetic_task_message_audit":{"supplied_sequences_or_hashes_found":sequence_transfer_detected},
    "credential_scan":{"passed":not secret_hits,"scope":"ordering and sequence evidence, including decoded Inspect logs"},
    "source_unchanged_since_rollout_start":all((ROOT/path).exists() and hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in record["source_sha256"].items()),
    "source_changes_since_rollout_start":[path for path,digest in record["source_sha256"].items() if not (ROOT/path).exists() or hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest],
    "source_sha256":record["source_sha256"],
    "source_sha256_at_validation":{path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in record["source_sha256"] if (ROOT/path).exists()},
    "post_rollout_change":"Ordering default message limit increased to 60 to accommodate seven DNA orders and optional sequence reads. The actual rollout explicitly used 60 already. Original ctf.py and run_eval.py are preserved under the run source/src directory.",
}
output=ROOT / "results/archive/ordering/validation.json"
output.write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({"tests":tests,"test_failures":failures,"model_samples":samples,"local_sequence_validation_passed":local["passed"],"credential_scan_passed":not secret_hits,"supplied_sequence_transfer_detected":sequence_transfer_detected},indent=2))
