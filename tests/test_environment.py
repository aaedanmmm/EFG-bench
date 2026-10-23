"""Tool contract tests; stores are local fixtures, simulator mocks are explicit."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from inspect_ai.scorer import INCORRECT, Target
from inspect_ai.tool import ToolError
from inspect_ai.util import Store
from src import environment
from src.scenarios import get_scenario
from src.scorer import ot2_mixture

REFERENCE = (Path(__file__).resolve().parents[1] / "examples/two_reagent_mix.py").read_text()


@pytest.fixture
def workspace(monkeypatch):
    current = Store({"scenario": get_scenario("two_reagent_mix"), "simulation_count": 0})
    monkeypatch.setattr(environment, "store", lambda: current)
    return current


def test_first_write_and_replacement(workspace):
    asyncio.run(environment.write_protocol()(REFERENCE))
    assert asyncio.run(environment.read_protocol()()) == REFERENCE
    workspace.set("final_validation", {"passed": True})
    asyncio.run(environment.write_protocol()("invalid replacement"))
    assert workspace.get("final_validation") is None
    assert workspace.get("protocol") == "invalid replacement"


def test_reject_empty_write_preserves_artifact(workspace):
    asyncio.run(environment.write_protocol()(REFERENCE))
    with pytest.raises(ToolError):
        asyncio.run(environment.write_protocol()(""))
    assert workspace.get("protocol") == REFERENCE


def test_simulation_budget_and_feedback(workspace, monkeypatch):
    # Mock simulator here tests the tool budget, not OT-2 correctness.
    async def mock_validation(code, scenario):
        return {"passed": False, "errors": ["constructed mock failure"], "events": ["full trace"], "opentrons_commands": ["mock command"]}
    monkeypatch.setattr(environment, "validate_code", mock_validation)
    asyncio.run(environment.write_protocol()(REFERENCE))
    for remaining in range(4, -1, -1):
        feedback = json.loads(asyncio.run(environment.simulate_protocol()()))
        assert feedback["simulations_remaining"] == remaining
        assert "events" not in feedback
    with pytest.raises(ToolError, match="budget exhausted"):
        asyncio.run(environment.simulate_protocol()())
    assert workspace.get("last_simulation")["events"] == ["full trace"]


def test_scorer_reruns_artifact_despite_claimed_success():
    wrong_code = REFERENCE.replace('transfer(15,', 'transfer(14,')
    state = SimpleNamespace(
        metadata={"scenario": get_scenario("two_reagent_mix")},
        store=Store({"protocol": wrong_code, "last_simulation": {"passed": True}, "final_validation": {"passed": True}}),
    )
    result = asyncio.run(ot2_mixture()(state, Target("")))
    assert result.value == INCORRECT
    assert result.metadata["passed"] is False
    assert result.metadata["tip_efficiency"] == 0
    assert "water expected 15 uL, got 14" in result.explanation
