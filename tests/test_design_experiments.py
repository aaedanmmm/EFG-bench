import pytest

from src.design_experiments import (
    experiment_quality,
    measure_yield,
    polymerases,
    public_experiment,
    run_experiment,
)


CONFIG = {
    "target_length_bp": 3000,
    "initial_yield_ng": 100,
    "yield_half_life_minutes": 60,
    "background_loss_per_junction": 0.1,
}


def test_public_run_hides_yield_and_assay_measures_the_aged_sample():
    run = run_experiment(CONFIG, "q5_polymerase", 2, 10)
    finish = run["finished_at_minutes"]
    public = public_experiment(run)
    assert set(public) == {
        "polymerase", "fragment_count", "started_at_minutes", "finished_at_minutes",
    }
    assert measure_yield(run, finish, CONFIG)["yield_ng"] == 90
    assert measure_yield(run, finish + 60, CONFIG) == {
        "measured_at_minutes": finish + 60, "age_minutes": 60, "yield_ng": 45,
    }
    fresh = experiment_quality(run, finish, CONFIG)
    aged = experiment_quality(run, finish + 120, CONFIG)
    assert aged["correct_yield_ng"] == pytest.approx(fresh["correct_yield_ng"] / 4)
    assert aged["correct_fraction"] == fresh["correct_fraction"]
    assert measure_yield(run, finish, CONFIG)["yield_ng"] == 90
    with pytest.raises(ValueError, match="has not finished"):
        measure_yield(run, finish - 1, CONFIG)


def test_polymerases_change_duration_and_sequence_fidelity_independently():
    taq = run_experiment(CONFIG, "taq_polymerase", 2, 0)
    q5 = run_experiment(CONFIG, "q5_polymerase", 2, 0)
    phusion = run_experiment(CONFIG, "phusion_polymerase", 2, 0)

    assert phusion["finished_at_minutes"] < q5["finished_at_minutes"] < taq["finished_at_minutes"]
    assert taq["correct_fraction"] < phusion["correct_fraction"] < q5["correct_fraction"] < 1
    assert taq["initial_yield_ng"] == q5["initial_yield_ng"] == phusion["initial_yield_ng"]
    assert taq["initial_correct_yield_ng"] < q5["initial_correct_yield_ng"]


def test_extra_fragments_cost_time_and_recover_less_product():
    two = run_experiment(CONFIG, "q5_polymerase", 2, 0)
    three = run_experiment(CONFIG, "q5_polymerase", 3, 0)
    assert three["finished_at_minutes"] == two["finished_at_minutes"] + 3
    assert three["initial_yield_ng"] == pytest.approx(two["initial_yield_ng"] * 0.9)
    assert three["correct_fraction"] == two["correct_fraction"]


def test_catalogue_profile_mutation_does_not_change_simulator():
    profiles = polymerases()
    original = profiles["q5_polymerase"]["error_per_base"]
    profiles["q5_polymerase"]["error_per_base"] = 1
    assert polymerases()["q5_polymerase"]["error_per_base"] == original
