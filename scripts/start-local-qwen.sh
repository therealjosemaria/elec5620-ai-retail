#!/usr/bin/env bash
set -euo pipefail

# Optional existing runtime/weights; no downloads or system-wide changes.
: "${LLAMA_SERVER_BIN:?Set LLAMA_SERVER_BIN to your installed llama-server executable}"
: "${LOCAL_QWEN_MODEL_PATH:?Set LOCAL_QWEN_MODEL_PATH to your existing Qwen GGUF}"
test -x "$LLAMA_SERVER_BIN"
test -f "$LOCAL_QWEN_MODEL_PATH"
qwen_runtime_dir="$(dirname "$LLAMA_SERVER_BIN")"
export LD_LIBRARY_PATH="$qwen_runtime_dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$LLAMA_SERVER_BIN" \
  --model "$LOCAL_QWEN_MODEL_PATH" \
  --alias "${LOCAL_QWEN_MODEL:-local-qwen}" \
  --host 127.0.0.1 --port "${LOCAL_QWEN_PORT:-18001}" \
  --ctx-size 4096 --threads "${LOCAL_QWEN_THREADS:-2}" --parallel 1 --no-webui
