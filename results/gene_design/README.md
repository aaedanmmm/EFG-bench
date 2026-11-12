# Gene design evidence

The historical runs below use a constructed, noncoding DNA target and simulated
purchases, reactions, and assays. The current default uses RB1; see
[RB1 reference and validation](../rb1_design/README.md).

## Actual rollout

Qwen3-8B scored **0/1**. It located an EcoRI site, ordered one 705 bp
fragment for $49.35, then submitted without running or measuring an assembly.
The independent replay reproduced the charge and failing score from the
accepted actions. [Inspect log](20261106T231831Z/2026-11-06T23-18-32-00-00_gene-design_gdp4cx2qhpQpas8buqvGDM.eval) ·
[Run configuration](20261106T231831Z/run.json) ·
[Replay evidence](20261106T231831Z/replay_validation.json)

## Historical local rollout configuration

These commands record the setup used before OpenRouter became required for new runs.

The model was Qwen3-8B Q4_K_M, served by llama.cpp build 6610 (8656f5de)
on the local loopback interface. The GGUF SHA-256 is
`d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
[Model weights](https://huggingface.co/Qwen/Qwen3-8B-GGUF/blob/main/Qwen3-8B-Q4_K_M.gguf)

Install the dependencies from `requirements-lock.txt` with Python 3.12.
Start the server with the downloaded GGUF.

```sh
llama-server --model /path/to/Qwen3-8B-Q4_K_M.gguf --host 127.0.0.1 \
  --port 18342 --alias Qwen3-8B-Q4_K_M --jinja --ctx-size 16384 \
  --parallel 1 --reasoning-format deepseek --reasoning-budget 0 \
  --chat-template-kwargs '{"enable_thinking":false}' --seed 42 --no-webui
```

Run Inspect from the repository root.

```sh
LLAMA_CPP_PYTHON_BASE_URL=http://127.0.0.1:18342/v1 \
  python -m src.run_eval --suite gene_design \
  --model llama-cpp-python/Qwen3-8B-Q4_K_M --limit 1 --message-limit 45 \
  --max-tokens 768 --output results/gene_design
```

The first attempt used port 18341, the model's default reasoning settings,
a 60-message limit, and 2,400 tokens per response. It was stopped during
quoting after seven minutes. [Interrupted Inspect log](20261106T231103Z/2026-11-06T23-11-04-00-00_gene-design_5QzAqbsqBtDMwAPtyVzRrh.eval) ·
[Run configuration](20261106T231103Z/run.json)

## Constructed controls

The [test output](validation.txt) covers the complete repository test suite.
The gene design tests verify exact reconstruction by both assembly routes,
pricing tier boundaries, purchase and clock limits, private yield, declining
assay readings, and fidelity and speed differences between polymerases.
