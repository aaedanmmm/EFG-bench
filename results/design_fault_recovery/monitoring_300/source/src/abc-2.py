"""Inspect AI agentic evaluation for generating and testing OT-2 protocols."""
import json
from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from src.environment import get_environment, initialise_environment, read_protocol, simulate_protocol, write_protocol, list_catalogue, order_supplies, read_sequence, list_human_services, request_human_service, replace_reagent, record_assessment
from src.scenarios import load_scenarios
from src.scorer import ot2_mixture
from src.ordering import public_scenario

AGENT_PROMPT = """You write Opentrons OT-2 Python protocols for synthetic reagent-mixing tasks.
Read get_environment for inventory, target volumes and the supported Python/API
subset. If supplies are missing, use list_catalogue and order_supplies to purchase
them within budget. For failure-recovery tasks, use diagnostic observations to
identify and repair persistent reaction faults.
Plan your transfers, save the complete code with write_protocol, test it
with simulate_protocol, and repair errors within the simulation budget. The saved
protocol.py is the graded artifact. Use submit when ready. Final prose is not code
submission. Do not claim experimental or biochemical validation from simulation.
"""


@task
def ot2_mixing(message_limit: int | None = 30, suite: str = "mixing", judge_model: str | None = None, judge_max_tokens: int = 8000,
               observation_mode: str = "deterministic", observation_seed: int = 0):
    from src.judge import contamination_judge
    from src.observations import make_suite
    if observation_mode not in ("deterministic", "ambiguous"):
        raise ValueError("Unknown observation mode")
    if observation_mode == "ambiguous" and suite != "failures":
        raise ValueError("Ambiguous observations require the failures suite")
    if observation_mode == "ambiguous" and judge_model:
        raise ValueError("The deterministic contamination judge is not calibrated for ambiguous observations")
    scenarios = load_scenarios(suite)
    if observation_mode == "ambiguous":
        scenarios = make_suite(scenarios, observation_seed)
    scorers = [ot2_mixture()]
    if judge_model:
        scorers.append(contamination_judge(model=judge_model, max_tokens=judge_max_tokens))
    return Task(
        dataset=[Sample(id=scenario["id"], input=scenario["description"] + "\nPrepare the exact targets described here:\n" + json.dumps(public_scenario(scenario), indent=2), metadata={"scenario": scenario}) for scenario in scenarios],
        solver=[initialise_environment(), react(prompt=AGENT_PROMPT, tools=[get_environment(), write_protocol(), read_protocol(), simulate_protocol()] + ([list_catalogue(), order_supplies(), read_sequence()] if suite in ("ordering", "biochemistry", "biochemistry_ordering", "failures") else []) + ([list_human_services(), request_human_service(), replace_reagent()] if suite == "failures" else []) + ([record_assessment()] if observation_mode == "ambiguous" else []), attempts=1)],
        scorer=scorers,
        message_limit=message_limit,
    )


# Preserve the scaffold's original task entry point.
@task
def intercode_ctf(message_limit: int = 30):
    return ot2_mixing(message_limit=message_limit)


@task
def ot2_ordering(message_limit: int = 60):
    return ot2_mixing(message_limit=message_limit, suite="ordering")


@task
def ot2_biochemistry(message_limit: int = 40):
    return ot2_mixing(message_limit=message_limit, suite="biochemistry")


@task
def ot2_biochemistry_ordering(message_limit: int = 60):
    return ot2_mixing(message_limit=message_limit, suite="biochemistry_ordering")


@task
def ot2_failures(message_limit: int = 90, judge_model: str | None = None,
                 observation_mode: str = "deterministic", observation_seed: int = 0):
    return ot2_mixing(message_limit=message_limit, suite="failures", judge_model=judge_model,
                     observation_mode=observation_mode, observation_seed=observation_seed)
