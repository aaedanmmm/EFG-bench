#!/bin/bash
# Retry only provider errors. Use the original run's shared ledger.
out=results/kimi_k3_budget10
python="${MATS_EVAL_PYTHON:-/private/tmp/mats-observation-env/bin/python}"
export XDG_DATA_HOME="$(mktemp -d /private/tmp/mats-k3-data.XXXXXX)"
export XDG_CACHE_HOME="$(mktemp -d /private/tmp/mats-k3-cache.XXXXXX)"
pids=()
for target in "$@"; do
  (
    suite="${target%%:*}"
    sample="${target#*:}"
    task="$suite"
    args=()
    if [[ "$suite" == failures_ambiguous ]]; then
      task=failures
      args=(--observation-mode ambiguous --observation-seed 41)
    fi
    export INSPECT_TRACE_FILE="$(mktemp /private/tmp/mats-k3-trace.XXXXXX)"
    "$python" -m src.run_eval --env-file .env --model openrouter/moonshotai/kimi-k3 \
      --suite "$task" --sample-id "$sample" --no-message-limit --budget-usd 10 \
      --budget-ledger "$out/budget.sqlite" --min-request-interval 15 --max-retries 6 \
      "${args[@]}" --output "$out/$suite"
  ) > "$out/retry-$target.console.txt" 2>&1 &
  pids+=("$!")
done
run_rc=0
for pid in "${pids[@]}"; do
  wait "$pid" || run_rc=1
done
exit "$run_rc"
