#!/bin/bash
# Run from the repository root. Credentials are loaded from .env.
out=results/kimi_k3_budget10
python="${MATS_EVAL_PYTHON:-/private/tmp/mats-observation-env/bin/python}"
export XDG_DATA_HOME="$(mktemp -d /private/tmp/mats-k3-data.XXXXXX)"
export XDG_CACHE_HOME="$(mktemp -d /private/tmp/mats-k3-cache.XXXXXX)"
pids=()
if [[ $# -eq 0 ]]; then
  set -- mixing ordering biochemistry biochemistry_ordering failures failures_ambiguous gene_design
fi
for suite in "$@"; do
  (
    args=()
    task="$suite"
    if [[ "$suite" = failures_ambiguous ]]; then
      task=failures
      args=(--observation-mode ambiguous --observation-seed 41)
    fi
    export INSPECT_TRACE_FILE="$(mktemp /private/tmp/mats-k3-trace.XXXXXX)"
    "$python" -m src.run_eval --env-file .env --model openrouter/moonshotai/kimi-k3 --suite "$task" --no-message-limit --budget-usd 10 --budget-ledger "$out/budget.sqlite" "${args[@]}" --output "$out/$suite"
    run_rc=$?
    printf '%s\n' "$run_rc" > "$out/$suite.exit"
    exit "$run_rc"
  ) > "$out/$suite.console.txt" 2>&1 &
  pids+=("$!")
done
run_rc=0
for pid in "${pids[@]}"; do
  wait "$pid" || run_rc=1
done
exit "$run_rc"
