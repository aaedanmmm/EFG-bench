"""Run each simulation in a disposable process with a timeout and no API keys."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from src.scenarios import ROOT


async def validate_code(code: str, scenario_id: str, timeout: int = 45, *, inventory: dict | None = None):
    with tempfile.TemporaryDirectory(prefix="ot2-eval-") as directory:
        protocol = Path(directory) / "protocol.py"
        protocol.write_text(code)
        command = [sys.executable, "-m", "src.validate", str(protocol), "--scenario", scenario_id]
        if inventory is not None:
            snapshot = Path(directory) / "inventory.json"
            snapshot.write_text(json.dumps(inventory))
            command.extend(["--inventory", str(snapshot)])
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=ROOT,
            env={"PATH": os.defpath, "OT_API_CONFIG_DIR": str(Path(directory) / "ot-config"), "PYTHONHASHSEED": "0"},
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except (TimeoutError, asyncio.CancelledError) as exc:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            if isinstance(exc, asyncio.CancelledError):
                raise
            return {"passed": False, "scenario_id": scenario_id, "errors": ["Simulator timed out"]}
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeError):
            return {"passed": False, "scenario_id": scenario_id, "errors": ["Simulator process failed"], "diagnostics": stderr.decode(errors="replace")[-4000:]}
        if process.returncode not in (0, 1) or (result.get("passed") and process.returncode != 0):
            result["passed"] = False
            result.setdefault("errors", []).append(f"Unexpected simulator exit status {process.returncode}")
        return result
