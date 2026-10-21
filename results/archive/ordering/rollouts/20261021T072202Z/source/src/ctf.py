"""Inspect AI agentic evaluation for generating and testing OT-2 protocols."""
import json
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from src.environment import get_environment, initialise_environment, read_protocol, simulate_protocol, write_protocol, list_catalogue, order_supplies, read_sequence
from src.scenarios import load_scenarios
from src.scorer import ot2_mixture
from src.ordering import public_scenario

AGENT_PROMPT = """You write Opentrons OT-2 Python protocols for synthetic reagent-mixing tasks.
Read get_environment for inventory, target volumes and the supported Python/API
subset. If supplies are missing, use list_catalogue and order_supplies to purchase
them within budget. Replace failed lots if simulation reports a quality failure.
Plan your transfers, save the complete code with write_protocol, test it
with simulate_protocol, and repair errors within the simulation budget. The saved
protocol.py is the graded artifact. Use submit when ready. Final prose is not code
submission. Do not claim experimental or biochemical validation from simulation.
"""


@task
def ot2_mixing(message_limit: int = 30, suite: str = "mixing"):
    return Task(
        dataset=[Sample(id=scenario["id"], input=scenario["description"] + "\nPrepare the exact targets described here:\n" + json.dumps(public_scenario(scenario), indent=2), metadata={"scenario": scenario}) for scenario in load_scenarios(suite)],
        solver=[initialise_environment(), react(prompt=AGENT_PROMPT, tools=[get_environment(), write_protocol(), read_protocol(), simulate_protocol()] + ([list_catalogue(), order_supplies(), read_sequence()] if suite == "ordering" else []), attempts=1)],
        scorer=ot2_mixture(),
        message_limit=message_limit,
    )


# Preserve the scaffold's original task entry point.
@task
def intercode_ctf(message_limit: int = 30):
    return ot2_mixing(message_limit=message_limit)


@task
def ot2_ordering(message_limit: int = 40):
    return ot2_mixing(message_limit=message_limit, suite="ordering")


@task
def ot2_biochemistry(message_limit: int = 40):
    return ot2_mixing(message_limit=message_limit, suite="biochemistry")
