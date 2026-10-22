# Engineering decisions

1. **Prove the local path first.** FastAPI + SQLite serve one owner and a same-origin TypeScript client. This fits the existing Windows environment, avoids recurring hosting cost and remains editable. Python 3.12 is selected over the installed3.15 default to use a mature dependency runtime; uv.lock fixes dependency versions.
2. **Use the documented web composer.** Meta documents standard text-entry activation and spatial navigation. We use semantic controls with visible focus and inline Confirm/Cancel actions; no simulated handwriting or custom D-pad event layer. Camera access remains a separate native track. See the full architecture matrix.
3. **Keep cloud use explicit.** Gemini uses the official SDK and configurable current model; the template disables both providers. The private local configuration enables only Ollama after real local verification. Account-level billing and data terms remain the owner's decision.
4. **Own conversation state.** SQLite stores messages, image bytes and outcomes. Only bounded recent text and one selected image go to the provider. This makes deletion, replay, provider switching and local operation understandable without provider-owned conversations or uploaded cloud files.
5. **Preserve uncertain outcomes.** Request IDs are transactionally reserved. Completed or failed outcomes replay consistently; startup marks interrupted work as uncertain, instead of silently spending another request. One active server process per data directory is required.
6. **Make images safe and manageable.** Verify decodable media, limit bytes/pixels, strip metadata and normalize size. Accept local uploads rather than arbitrary image URLs, eliminating a remote-fetch SSRF surface. HEIC conversion is explicit.
7. **Separate device access from model credentials.** The root token stays in local configuration; browsers receive only a workspace token. Numeric one-use codes avoid a long password entry on glasses. Paired devices are the same owner's trusted clients, not separate tenants.
8. **Prefer measured evidence.** Mocked SDK tests verify transport and failures. Browser checks verify the real API/UI. Live Ollama calls verify real text and image inference on this laptop. Gemini credentials, HTTPS deployment and device interaction remain separate gates.

## Next milestones

1. Owner obtains a Gemini key and checks plan/data-use settings; test actual text and image responses.
2. Approve a temporary HTTPS route, pair the available glasses and run the hardware acceptance checklist.
3. Validate handwritten follow-ups, image selection and display readability on real firmware before claiming the wearable workflow works.
4. Secure access to macOS/Xcode and signing if pursuing native iPhone camera capture. Use current official DAT interfaces and explicitly validate lifecycle/session handoff; no unsupported bridge is assumed.
5. Only after the core workflow works, evaluate stronger local models, streaming, search and permission-scoped coding-agent features. No model currently receives tools or command execution.
