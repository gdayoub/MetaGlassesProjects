# AI model and inference findings

Checked against official documentation on **2026-10-22**. Published capabilities are not an accuracy benchmark or a successful call using this account. Gemini has not been live-tested because no API credential was available. See the quality report for local Ollama test results.

## Model choice

| Candidate | Verified capabilities and current status | LensAgent decision |
|---|---|---|
| `gemini-3.5-flash-lite` | Stable; text/image/video/audio/PDF input and text output. 1,048,576 input and 65,536 output token limits. July 2026 model update. [Official model card](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) | Default configurable Gemini model for concise visual questions. Published low-latency positioning; no measured end-to-end latency here. |
| `gemini-3.8-flash` | Stable September 2026 model; same input modalities, supports reasoning and coding. [Official model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) | Optional replacement through `GEMINI_MODEL`; evaluate accuracy/cost on representative handwriting, math and diagrams before switching. |
| Gemini 2.5 models | Official deprecation page restricts access to existing users and recommends newer models for new projects. [Deprecations](https://ai.google.dev/gemini-api/docs/deprecations) | Do not start a new project on remembered 2.5-era identifiers. |
| Ollama `gemma3:4b` | Vision variant listed as 3.4 GB, text/image input, requires Ollama 0.6+. 270m/1b variants are text-only. [Official Ollama model listing](https://ollama.com/library/gemma3) | Conservative local fallback for this Windows laptop (32 GB RAM, RTX 5070 Laptop GPU). Small download and established vision support informed selection; this is not a claim that it is the newest or best model. |

The current [Ollama vision documentation](https://docs.ollama.com/capabilities/vision) uses Gemma 4 examples. LensAgent accepts an administrator-configured model identifier, so upgrading requires no transport rewrite. Capability/quality must be checked for the exact installed tag. Neither a GPU name nor a model description proves real-world OCR, mathematical notation, or diagram accuracy; measure these with user-representative photographs.

## Cost, quotas and data

The [Gemini pricing table](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite) lists free input/output for Gemini 3.5 Flash-Lite, subject to account eligibility and quotas. Its standard paid rates are **$0.30 per million input tokens** (including images) and **$2.50 per million output tokens**, including thinking. This does not make a paid-tier project free. LensAgent does not enable billing, buy credits, use paid tools, or choose a paid model automatically.

[Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) vary by model, project and tier; the active values must be read in AI Studio. Do not rely on old fixed free-tier RPM/RPD figures. Google's daily quota resets at midnight Pacific; LensAgent's separate local daily counter resets at midnight UTC. A local counter is an additional guard, not an account-level billing guarantee.

[Billing documentation](https://ai.google.dev/gemini-api/docs/billing) says new Google Cloud Welcome/free-trial credits cannot pay for Gemini API/AI Studio usage from March 2026. Older eligible credits have their own expiry; other promotional credits require eligibility verification. With Prepay, eligible Cloud credits require an active prepaid balance. No credit eligibility was confirmed for this user's account, and no billing changes were made.

[Gemini terms](https://ai.google.dev/gemini-api/terms) permit product improvement and human review for unpaid services and instruct users not to submit sensitive, confidential or personal information. Regional exceptions and paid-service terms differ; check the actual account. Local deletion cannot undo data already sent to a cloud provider. For private images, use the enabled local Ollama route without cloud transmission.

## Implemented transport and limits

The backend uses the official [`google-genai` Python SDK](https://ai.google.dev/gemini-api/docs/libraries), pinned at 2.32.0. It calls `models.generate_content` with typed `Content` and `Part` objects. Google now labels this API documentation **Legacy**, but its [current image-understanding examples](https://ai.google.dev/gemini-api/docs/generate-content/image-understanding) still document this endpoint with current models. The guide states a 20 MB total inline request ceiling. We selected stateless calls with application-owned SQLite history to avoid cloud conversation/file lifecycle dependencies. Revisit the Interactions API when a concrete needed capability justifies migrating.

LensAgent accepts JPEG/PNG/WebP uploads up to 5 MiB and 20 megapixels, verifies decoding, strips metadata, downsamples to 2048 pixels on the longest edge, and sends one selected image inline. This stays comfortably below the documented request ceiling. Normalization can reduce fine handwriting detail: crop the relevant region first when necessary. GIF/HEIC, animation, URLs, video, PDFs and arbitrary URL fetching are not supported by this endpoint.

The [Ollama chat API](https://docs.ollama.com/api/chat) receives the history and a base64 `images` array with `stream:false`, a bounded output limit and 8192-token local context setting. The server URL is restricted to local HTTP loopback and redirects/proxy environment variables are disabled. The API does not accept a caller-provided provider URL, model name, command, tool definition or path.

Current defaults: 45-second provider network timeout; one additional Gemini attempt only on explicit 429/503 responses; no automatic timeout resend; 768 maximum output tokens; at most 12 historic messages and 16,000 historical characters plus the current question; 100 accepted requests per UTC day and 10 per minute. A Gemini retry can create a second upstream attempt, so the local request counter is not an exact upstream quota meter. Usage logs contain provider and token counts, not images, keys or conversation text. `GEMINI_ENABLED=false` and `OLLAMA_ENABLED=false` in the template require intentional provider activation.

## Confidence and next validation

- **Implemented and unit/integration tested:** text/image serialization using the installed official SDK and mocked HTTP transport; bounded history; image follow-up, replacement, selection and clearing; provider switching; failure sanitization, bounded retry behavior, quotas and persistence.
- **Gemini live API: pending.** Configure a valid key locally, verify free-tier plan/quotas and data handling, enable Gemini, then test a non-sensitive text prompt and image through the full application. No successful cloud inference is implied by SDK serialization tests.
- **Ollama live API:** consult `docs/quality/test-report.md`; the project coordinator performs hardware-local inference separately from these mocked transport tests.
- **Glasses hardware: not yet verified.** Model capability does not establish camera delivery, silent text entry or display output.
- **Future providers:** implement the small `Provider.generate(history, image) -> Generation` protocol. OpenAI/Claude/Codex adapters are not implemented. Coding-agent execution remains out of scope and no model output can execute local commands.
