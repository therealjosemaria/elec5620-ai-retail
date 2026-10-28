# Optional local Qwen fallback

The university `campus-qwen` endpoint remains primary. The owner requested the
existing server model as a fallback when the university service is unavailable,
unreachable, timing out or rejecting calls for capacity.
The inspected Pi has Qwen2.5-1.5B-Instruct Q4_K_M weights and a llama.cpp server
binary already installed; no model download or new inference package was needed.
The local model is smaller and its quality/performance may differ.

## Start an existing runtime

```bash
LLAMA_SERVER_BIN=/absolute/path/to/llama-server \
LOCAL_QWEN_MODEL_PATH=/absolute/path/to/qwen-model.gguf \
bash scripts/start-local-qwen.sh
```

This binds only `127.0.0.1:18001`, uses two CPU threads, one inference slot and
a 4,096-token context. The script sets the runtime's shared-library path locally
for that process. It installs nothing and does not change unrelated applications.
Stop with Ctrl-C; after a host restart, run the command again. It is optional for
teammates and the submission; weights/runtime are not committed to Git.

Configure the application's private `.env` and restart FastAPI:

```dotenv
LOCAL_QWEN_FALLBACK_ENABLED=true
LOCAL_QWEN_BASE_URL=http://127.0.0.1:18001/v1
LOCAL_QWEN_MODEL=local-qwen
```

The example environment defaults to disabled. University credentials stay private.
The default local placeholder API key is not a university credential. Keep the
inference endpoint on localhost.

## Routing policy

- Every new live operation tries university Qwen first. `LIVE_DAILY_LIMIT=unlimited`
  removes the application's daily cap; university-enforced limits still apply.
  Usage counting and saved-result reuse remain active.
- Connection errors, timeouts, HTTP 408/429, server errors (5xx) and explicit quota
  rejection permit one local fallback. Provider/model/reason are saved and shown.
- The next new operation tries university again. There is no day-long local latch;
  historical quota-state rows are ignored. Cached results never generate again.
- Authentication/permission errors (except an explicit quota code), malformed
  requests, wrong endpoints, truncation and invalid output do not trigger fallback.
- An optional numeric application cap is still supported for isolated tests. It
  rejects new calls at the configured count; reaching it does not select local.
- Local failures remain explicit. Both providers use the same evidence validation,
  durable recommendation cache and zero automatic retry policy. An ambiguous
  timeout may already have consumed university tokens; the local fallback is
  recorded as a different provider, not a free university retry.

Captured requests and saved recommendations record `model_provider`, `model_name`
and `fallback_reason`. The UI shows these fields so local results are never
presented as university results. `mode=live` means model inference was used;
the provider field identifies which model actually answered.

## Output controls and limitations

The proxy schema rejected provider-specific `enable_thinking` and
`chat_template_kwargs` fields. It accepted standard `reasoning_effort=none`.
The client uses that standard control for university calls and includes Qwen's
documented `/no_think` instruction. Non-zero temperature avoids greedy-loop risk
described in Qwen's documentation. This does not assume all campus backends share
the same underlying Qwen variant.

The installed LangChain client normalizes token limits to `max_completion_tokens`;
the university guide uses `max_tokens`. The transport sends only `max_tokens`
through `extra_body`, because the proxy rejects requests containing both fields:
2,048 for capture and 4,096 for recommendations, with at most three recommended
products. These are ceilings, not requested output lengths. No raw reasoning or
provider output is logged. Truncation logs contain only provider/token metrics.

University timeout remains 30 seconds. The CPU fallback allows 120 seconds and
may not meet the provisional 10-second target. Check `VERIFICATION.md` for actual
local/provider measurements; a small API health check alone does not establish
recommendation quality or end-to-end performance.

On 28 October the actual local capture → recommendation → inventory workflow
and cached rerun completed in 39.8 seconds with zero university calls. The sample
capture omitted a stated constraint; earlier samples paraphrased numbers and were
rejected by source validation. Treat this small model as a lower-quality fallback,
not equivalent to campus Qwen. The provisional 10-second target is not met by
this full local sample. See the verification record for exact scope.

The university connection guides are private because they contain credentials.
Public reference: [Qwen controls and sampling guidance](https://qwen.readthedocs.io/en/stable/getting_started/quickstart.html).
