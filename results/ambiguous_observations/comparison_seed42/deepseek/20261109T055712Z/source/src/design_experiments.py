"""Deterministic, constructed time and yield model for the design benchmark."""
import math


FIDELITY_SOURCE = "https://www.neb.com/en/tools-and-resources/selection-charts/dna-polymerase-selection-chart"
_POLYMERASES = {
    "taq_polymerase": {
        "error_per_base": 1.5e-4,
        "extension_seconds_per_kb": 60,
        "extension_source": "https://www.neb.com/protocols/taq-dna-polymerase-with-thermopol-buffer-m0267",
    },
    "q5_polymerase": {
        "error_per_base": 5.3e-7,
        "extension_seconds_per_kb": 25,
        "extension_source": "https://www.neb.com/en-us/protocols/pcr-using-q5-high-fidelity-dna-polymerase-m0491",
    },
    "phusion_polymerase": {
        "error_per_base": 3.9e-6,
        "extension_seconds_per_kb": 15,
        "extension_source": "https://www.neb.com/en-us/protocols/pcr-protocol-m0530",
    },
}


def polymerases():
    """Return isolated copies of the public, supplier-derived profiles."""
    return {
        name: {**profile, "fidelity_source": FIDELITY_SOURCE}
        for name, profile in _POLYMERASES.items()
    }


def _nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return value


def run_experiment(config, polymerase, fragment_count, clock_minutes):
    """Create a snapshot of a run; callers advance the clock to its finish."""
    if not isinstance(polymerase, str) or polymerase not in _POLYMERASES:
        raise ValueError("Choose a polymerase from the catalogue")
    if type(fragment_count) is not int or fragment_count < 1:
        raise ValueError("fragment_count must be a positive integer")
    length = config["target_length_bp"]
    if type(length) is not int or length < 1:
        raise ValueError("target_length_bp must be a positive integer")
    start = _nonnegative(clock_minutes, "clock_minutes")
    baseline_yield = _nonnegative(config["initial_yield_ng"], "initial_yield_ng")
    junction_loss = _nonnegative(
        config.get("background_loss_per_junction", 0.05), "background_loss_per_junction"
    )
    if junction_loss > 1:
        raise ValueError("background_loss_per_junction cannot exceed 1")

    profile = _POLYMERASES[polymerase]
    # Extension times parameterize a virtual duration with fixed overhead and
    # per-fragment setup. They are inputs to the simulator's clock.
    extension_minutes = 30 * (length / 1000) * profile["extension_seconds_per_kb"] / 60
    duration = math.ceil(15 + 3 * fragment_count + extension_minutes)
    # The aggregate fidelity model uses one effective copying pass with
    # independent per-base errors. Junction loss models recovered product mass.
    correct_fraction = (1 - profile["error_per_base"]) ** length
    total_yield = baseline_yield * (1 - junction_loss) ** (fragment_count - 1)
    return {
        "polymerase": polymerase,
        "fragment_count": fragment_count,
        "started_at_minutes": start,
        "finished_at_minutes": start + duration,
        "initial_yield_ng": total_yield,
        "initial_correct_yield_ng": total_yield * correct_fraction,
        "correct_fraction": correct_fraction,
    }


def public_experiment(experiment):
    """Expose run metadata with an allowlist so private fields stay private."""
    return {
        key: experiment[key]
        for key in ("polymerase", "fragment_count", "started_at_minutes", "finished_at_minutes")
    }


def experiment_quality(experiment, clock_minutes, config):
    """Evaluate exact simulated quality at a given time for private scoring."""
    measured_at = _nonnegative(clock_minutes, "clock_minutes")
    age = measured_at - experiment["finished_at_minutes"]
    if age < 0:
        raise ValueError("The experiment has not finished")
    half_life = _nonnegative(config["yield_half_life_minutes"], "yield_half_life_minutes")
    if half_life == 0:
        raise ValueError("yield_half_life_minutes must be positive")
    remaining_fraction = 2 ** (-age / half_life)
    return {
        "yield_ng": experiment["initial_yield_ng"] * remaining_fraction,
        "correct_yield_ng": experiment["initial_correct_yield_ng"] * remaining_fraction,
        "correct_fraction": experiment["correct_fraction"],
    }


def measure_yield(experiment, clock_minutes, config):
    """Return the simulated assay observation without revealing sequence fidelity."""
    quality = experiment_quality(experiment, clock_minutes, config)
    return {
        "measured_at_minutes": clock_minutes,
        "age_minutes": clock_minutes - experiment["finished_at_minutes"],
        "yield_ng": round(quality["yield_ng"], 3),
    }
