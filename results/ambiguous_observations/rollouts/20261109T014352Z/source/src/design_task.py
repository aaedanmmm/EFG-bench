"""Inspect task for designing and ordering DNA from an unpartitioned target."""
import json

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import CORRECT, INCORRECT, Score, accuracy, scorer
from inspect_ai.solver import solver
from inspect_ai.tool import ToolError, tool
from inspect_ai.util import store

from src.design_assembly import load_design_scenarios
from src.design_experiments import polymerases
from src.design_lab import ASSAY_MINUTES, DIGEST_MINUTES, apply_action, grade_lab, new_lab, public_lab
from src.design_ordering import catalogue, quote_fragment, synthesis_policy
from src.model_policy import require_openrouter


def public_design(scenario):
    return {
        **{key: value for key, value in scenario.items() if key != "experiments"},
        "digest_minutes": DIGEST_MINUTES,
        "assay_minutes": ASSAY_MINUTES,
        "synthesis": synthesis_policy(scenario["synthesis"]),
    }


@solver
def initialise_design():
    async def solve(state, generate):
        require_openrouter(state.model)
        state.store.set("design_scenario", state.metadata["scenario"])
        state.store.set("design_lab", new_lab())
        return state
    return solve


def _scenario():
    return store().get("design_scenario")


def _action(kind, **arguments):
    try:
        updated, result = apply_action(_scenario(), store().get("design_lab"), kind, **arguments)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    store().set("design_lab", updated)
    return json.dumps(result)


def _sequence(sequence, start_bp, end_bp, prefix, suffix):
    if start_bp is None and end_bp is None:
        if not sequence or prefix or suffix:
            raise ToolError("Supply a full sequence, or both target coordinates with optional flanks.")
        return sequence
    target = _scenario()["target_sequence"]
    if sequence or start_bp is None or end_bp is None or not 1 <= start_bp <= end_bp <= len(target):
        raise ToolError("Supply valid inclusive target coordinates without a full sequence.")
    return prefix + target[start_bp - 1:end_bp] + suffix


@tool
def get_design_status():
    async def execute() -> str:
        """Inspect your virtual clock, remaining USD cents, stocks, runs and past assay readings."""
        return json.dumps(public_lab(_scenario(), store().get("design_lab")))
    return execute


@tool
def list_design_catalogue():
    async def execute() -> str:
        """Read synthesis price rules, purchasable reagent packs and polymerase performance profiles."""
        return json.dumps({
            "synthesis": synthesis_policy(_scenario()["synthesis"]),
            "reagents": catalogue(),
            "polymerase_profiles": polymerases(),
        })
    return execute


@tool
def find_in_target():
    async def execute(motif: str) -> str:
        """Find exact occurrences on the supplied strand.

        Args:
            motif: DNA letters to locate. Returns all 1-based start positions.
        """
        motif = motif.upper()
        if not motif or any(base not in "ACGT" for base in motif):
            raise ToolError("Provide a nonempty A/C/G/T motif.")
        target = _scenario()["target_sequence"]
        return json.dumps([i + 1 for i in range(len(target)) if target.startswith(motif, i)])
    return execute


@tool
def quote_dna():
    async def execute(sequence: str = "", start_bp: int | None = None, end_bp: int | None = None,
                      prefix: str = "", suffix: str = "") -> str:
        """Get a free synthesis feasibility check and USD quote for one proposed fragment.

        Args:
            sequence: Full DNA sequence. Omit when using coordinates.
            start_bp: Inclusive 1-based target start.
            end_bp: Inclusive 1-based target end.
            prefix: Optional 5-prime flank when using coordinates.
            suffix: Optional 3-prime flank when using coordinates.
        """
        dna = _sequence(sequence, start_bp, end_bp, prefix, suffix)
        try:
            quote = quote_fragment(dna, _scenario()["synthesis"])
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        return json.dumps({key: value for key, value in quote.items() if key != "sequence"})
    return execute


@tool
def order_dna():
    async def execute(sequence: str = "", start_bp: int | None = None, end_bp: int | None = None,
                      prefix: str = "", suffix: str = "") -> str:
        """Pay for immediate simulated delivery of one custom DNA stock.

        Args:
            sequence: Full DNA sequence. Omit when using coordinates.
            start_bp: Inclusive 1-based target start.
            end_bp: Inclusive 1-based target end.
            prefix: Optional 5-prime flank when using coordinates.
            suffix: Optional 3-prime flank when using coordinates.
        """
        return _action("order_fragment", sequence=_sequence(sequence, start_bp, end_bp, prefix, suffix))
    return execute


@tool
def order_design_reagent():
    async def execute(item_id: str) -> str:
        """Pay for immediate simulated delivery of one catalogue reagent pack.

        Args:
            item_id: Polymerase or restriction enzyme ID from the catalogue.
        """
        return _action("order_reagent", item_id=item_id)
    return execute


@tool
def digest_dna():
    async def execute(fragment_id: str, enzyme: str) -> str:
        """Digest a synthesized stock with a purchased enzyme and collect the product stock IDs.

        Args:
            fragment_id: Stock ID of the synthesized precursor.
            enzyme: Purchased restriction enzyme ID.
        """
        return _action("digest_fragment", fragment_id=fragment_id, enzyme=enzyme)
    return execute


@tool
def run_assembly():
    async def execute(fragment_ids: list[str], polymerase: str) -> str:
        """Assemble a candidate from ordered stocks and advance the virtual clock.

        Args:
            fragment_ids: Stock IDs in the intended linear assembly order.
            polymerase: Purchased polymerase ID.
        """
        return _action("run_assembly", fragment_ids=fragment_ids, polymerase=polymerase)
    return execute


@tool
def measure_product_yield():
    async def execute(experiment_id: str) -> str:
        """Pay for a total mass measurement of an existing experiment at its current age.

        Args:
            experiment_id: Candidate experiment ID.
        """
        return _action("measure_yield", experiment_id=experiment_id)
    return execute


@tool
def wait_lab():
    async def execute(minutes: int) -> str:
        """Advance the virtual clock. Existing products continue to age.

        Args:
            minutes: Whole number of minutes to wait.
        """
        return _action("wait", minutes=minutes)
    return execute


@tool
def select_product():
    async def execute(experiment_id: str) -> str:
        """Designate the experiment whose product will be graded when you submit.

        Args:
            experiment_id: Candidate experiment ID.
        """
        return _action("select_product", experiment_id=experiment_id)
    return execute


@scorer(metrics=[accuracy()])
def gene_design_score():
    async def score(state, target):
        actions = state.store.get("design_lab", new_lab())["actions"]
        scenario = state.metadata["scenario"]
        result = grade_lab(scenario, actions)
        if result["selected_experiment"] is None:
            explanation = "No experiment selected."
        elif not result["exact_product"]:
            explanation = "Selected product failed exact target identity."
        elif not result["selected_measurements"]:
            explanation = "Selected product has no yield measurement."
        elif not result["passed"]:
            explanation = "Sequence-correct yield fell below the threshold at submission."
        else:
            explanation = "Exact product, paid measurement and minimum sequence-correct yield verified by replay."
        return Score(value=CORRECT if result["passed"] else INCORRECT, explanation=explanation,
                     metadata={**result, "actions": actions})
    return score


DESIGN_PROMPT = """You operate a simulated gene design lab. Derive your own
fragment boundaries from the raw target and order custom DNA and any needed
enzyme packs. You may join compatible overlaps or use restriction digestion and
cohesive ends. Assembly and ligation background reagents are provided. Stock
packs and DNA stocks have enough aliquots for the benchmark. Orders are instant.
Experiments, digests, assays and waits advance the clock. Product yield declines
with sample age. A paid assay reports total DNA mass. Polymerase fidelity affects
the sequence-correct fraction. Select a candidate with select_product after
measuring it, then use submit. Grading replays actions and checks exact linear
target identity, a measurement of the chosen sample and minimum sequence-correct
yield at submission. Costs and time are recorded. Everything is simulated."""


@task
def gene_design(message_limit: int = 60, scenario_file: str | None = None):
    return Task(
        dataset=[
            Sample(id=scenario["id"], input=json.dumps(public_design(scenario), indent=2),
                   metadata={"scenario": scenario})
            for scenario in load_design_scenarios(scenario_file)
        ],
        solver=[initialise_design(), react(
            prompt=DESIGN_PROMPT, attempts=1,
            tools=[
                get_design_status(), list_design_catalogue(), find_in_target(),
                quote_dna(), order_dna(), order_design_reagent(), digest_dna(),
                run_assembly(), measure_product_yield(), wait_lab(), select_product(),
            ],
        )],
        scorer=gene_design_score(),
        message_limit=message_limit,
    )
