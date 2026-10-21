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
                if scenario.get("failure_modes"):
                    from src.failures import replay_lab_actions
                    inventory, account = replay_lab_actions(scenario, state.store.get("lab_actions", []))
                else:
                    inventory, account = replay_orders(scenario, stored_account["orders"] if stored_account else [])
            except (OrderError, KeyError, TypeError) as exc:
                return Score(value=INCORRECT, explanation=f"Invalid ordering ledger: {exc}", metadata={"passed": False})
            report = await validate_code(code, scenario["id"], inventory=inventory)
        else:
            report = await validate_code(code, scenario["id"])
        if scenario.get("failure_modes"):
            from src.failures import recovery_evidence
            try:
                recovery = recovery_evidence(scenario, state.store.get("lab_actions", []), state.store.get("experiments", []), state.store.get("assays", []), code, report, inventory)
            except (OrderError, KeyError, TypeError, ValueError) as exc:
                recovery = {"passed": False, "errors": [f"Invalid recovery evidence: {exc}"]}
            report["recovery"] = recovery
            if not recovery["passed"]:
                report["passed"] = False
                report["errors"].append("Recovery requires observing a failed reaction gel and verifying the current repaired protocol/inventory with a fresh reaction gel")
            report["lab_actions"] = state.store.get("lab_actions", [])
        if account is not None:
            report["ordering"] = account_summary(account)
            report["cost_efficiency"] = (1 - account["spent_cents"] / account["budget_cents"]) if report["passed"] else 0.0
        report["score_breakdown"] = {"overall": int(report["passed"]), "liquid_handling": int(report.get("liquid_handling_passed", False)), "biochemistry": int(report["biochemistry"]["passed"]) if report.get("biochemistry", {}).get("applicable") else None}
        if scenario.get("sequence_inventory"):
            report["sequence_inventory"] = scenario["sequence_inventory"]
            report["sequence_interpretation"] = "Declared synthetic biochemical sequence inputs; acceptance is in silico, experimental success unmeasured" if scenario.get("biochemistry") else "Sequence-linked liquid handling only; no assembly design or experimental success inferred"
        report["protocol_source"] = code
        report["simulation_count"] = state.store.get("simulation_count", 0)
        report["tip_efficiency"] = (1 - report.get("tips_used", 0) / (scenario["tip_budget"] + 1)) if report["passed"] else 0.0
        state.store.set("final_validation", report)
        return Score(
            value=CORRECT if report["passed"] else INCORRECT,
            explanation=("Liquid handling and all biochemical acceptance gates passed (in silico; experimental outcome unmeasured)" if report.get("biochemistry", {}).get("applicable") else "All virtual-robot and liquid-accounting checks passed; no biochemical model configured") if report["passed"] else "; ".join(report["errors"]),
            metadata=report,
        )
    return score
