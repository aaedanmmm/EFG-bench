"""Grade the artifact by fresh execution, never by the agent's claimed success."""
from inspect_ai.scorer import CORRECT, INCORRECT, Score, accuracy, scorer, stderr
from src.runner import validate_code
from src.ordering import OrderError, account_summary, replay_orders


@scorer(metrics=[accuracy(), stderr()])
def ot2_mixture():
    async def score(state, target):
        code = state.store.get("protocol", "")
        scenario = state.metadata["scenario"]
        if not code:
            return Score(value=INCORRECT, explanation="No protocol saved", metadata={"passed": False})
        account = None
        if scenario.get("ordering"):
            try:
                stored_account = state.store.get("ordering_account")
                inventory, account = replay_orders(scenario, stored_account["orders"] if stored_account else [])
            except (OrderError, KeyError, TypeError) as exc:
                return Score(value=INCORRECT, explanation=f"Invalid ordering ledger: {exc}", metadata={"passed": False})
            report = await validate_code(code, scenario["id"], inventory=inventory)
        else:
            report = await validate_code(code, scenario["id"])
        if account is not None:
            report["ordering"] = account_summary(account)
            report["cost_efficiency"] = (1 - account["spent_cents"] / account["budget_cents"]) if report["passed"] else 0.0
        report["protocol_source"] = code
        report["simulation_count"] = state.store.get("simulation_count", 0)
        report["tip_efficiency"] = (1 - report.get("tips_used", 0) / (scenario["tip_budget"] + 1)) if report["passed"] else 0.0
        state.store.set("final_validation", report)
        return Score(
            value=CORRECT if report["passed"] else INCORRECT,
            explanation="All virtual-robot and liquid-accounting checks passed" if report["passed"] else "; ".join(report["errors"]),
            metadata=report,
        )
    return score
