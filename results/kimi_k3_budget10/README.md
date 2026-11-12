# Kimi K3 benchmark with a shared $10 USD ceiling

This is a fresh rollout across the seven configurations documented in the project README, with 19 samples configured. The earlier run with default message limits is [recorded separately](../kimi_k3_full/README.md).

The actor is `openrouter/moonshotai/kimi-k3`. The run disables the message limit and preserves the existing 5,000 output tokens per generation, temperature 0, one sample and one model connection per suite, and artifact-based scoring. Ambiguous recovery uses observation seed 41. The optional model judge is disabled.

The seven suites share one SQLite budget. Before dispatching a generation, the guard reserves the full model context at the allowed maximum input rate plus the request's output-token cap at the allowed maximum output rate. Eligible OpenRouter routes publish no request or cache-write fee and price cache reads below uncached input. The ledger settles the reservation against the reported charge and conservatively holds an unconfirmed charge. A sample is marked cost-limited if the next reservation would breach $10 after settled and unconfirmed charges. The guard can therefore stop below $10. The largest reservation at the configured rates and output cap is $1.128576.

OpenRouter reported an eight-request-per-minute limit. Inspect's retry allowance was raised from one to six on the two active recovery processes. Samples that failed with a provider error were rerun with a 15-second minimum interval shared by the retry processes and the original ledger. The report preserves all attempts and sums their charges. It uses the scored attempt for each unique sample.

## Results

Kimi K3 passed **17 of 19 tasks (89.5%)** in **31 minutes 32 seconds** of wall-clock time. OpenRouter charged **$4.15 USD** for 256 generations, including partial attempts and retries. Both failures were in ambiguous recovery.

| Suite | Passed | OpenRouter cost |
| --- | ---: | ---: |
| Mixing | 3/3 | $0.104 |
| Ordering | 2/2 | $0.141 |
| Supplied-sequence assembly | 1/1 | $0.077 |
| Assembly with ordering | 1/1 | $0.090 |
| Deterministic recovery | 5/5 | $0.921 |
| Ambiguous recovery | 4/6 | $2.453 |
| Gene design | 1/1 | $0.368 |

## Reproduce

From the repository root, use Python 3.12 with the root dependencies and set the OpenRouter credential in the environment or uncommitted `.env`. Point `MATS_EVAL_PYTHON` to that environment's interpreter. For a separate run, use a fresh output directory and ledger path in the launcher. Reusing a ledger carries over its spending and outstanding reservations.

```sh
/bin/bash results/kimi_k3_budget10/run.sh
# When reproducing a provider-error retry, use the same ledger:
# /bin/bash results/kimi_k3_budget10/retry.sh suite:sample_id
python results/kimi_k3_budget10/summarize.py
python results/kimi_k3_budget10/fetch_billing.py
python results/kimi_k3_budget10/summarize.py
PYTHONPATH=. python results/kimi_k3_budget10/replay_scores.py
python -m pytest -q tests --junitxml=results/kimi_k3_budget10/tests.xml
```

Each suite has an Inspect log and run record with the model, source hashes and effective configuration. [summary.json](summary.json) groups artifact scores, timings, provider charges and simulated lab spending. [budget.sqlite](budget.sqlite) records reservations and settlements. API charges are in USD. The benchmark grades simulated outcomes.

## Validation

- [Constructed one-cent control](constructed_budget_control/console.txt) · Inspect recorded a cost stop before an API request. The control used a placeholder credential and produced no model rollout.
- [Budget unit tests](budget_tests.txt) · Shared reservation, persistence and dispatch pacing.
- [Primary source snapshot](source.tar.gz) and [retry source snapshot](retry_source.tar.gz) · Verified against the corresponding run records.
- [Final regression suite](final_tests.txt) · 246 passed.
- [Score replay](score_replay.json) · Reproduced all 19 scored outcomes.
- [Ledger validation](validation.json) and [OpenRouter generation records](generation_billing.json) · Every settled charge fit its reservation, with no pending or unconfirmed charges. Generation records were available for all 256 calls that produced a generation.
