#!/usr/bin/env bash
# Run the `failures` suite (all 5 constructed failure modes: inactive ligase,
# damaged DNA, absent DNA, +12C offset, -12C offset) once per model.
#
# Usage:
#   ./scripts/run_failures_models.sh [env-file]
#
# env-file defaults to ../MATS-work-test/.env (sibling checkout holding
# OPENROUTER_API_KEY), matching the command in README.md. Override by passing
# a path, e.g.: ./scripts/run_failures_models.sh .env

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

ENV_FILE="${1:-../MATS-work-test/.env}"
OUTPUT_DIR="results/failures/rollouts"

MODELS=(
  "openrouter/moonshotai/kimi-k3"
  "openrouter/deepseek/deepseek-v4.1-flash-1017"
  "openrouter/openai/gpt-6-luna"
  "openrouter/anthropic/claude-haiku-5.5"
  "openrouter/meta-llama/llama-3.3-70b-instruct"
)

for model in "${MODELS[@]}"; do
  echo "=== Running failures suite on ${model} ==="
  .venv/bin/python -m src.run_eval \
    --env-file "${ENV_FILE}" \
    --model "${model}" \
    --suite failures \
    --output "${OUTPUT_DIR}"
done
