# Test and engineering review report

Executed on 2026-10-22, Windows 11, Python 3.12.10, Node 24.19.0, Microsoft Edge, Ollama 0.40.6. This report distinguishes real inference from test doubles and device evidence.

## Results

| Verification | Actual result |
|---|---|
| Backend pytest | **46 passed**; includes 10 independent security checks. Real FastAPI/SQLite/image pipeline, explicit injected providers and actual Gemini SDK through mocked HTTP. |
| Fresh environment | Exported frozen uv lock, installed into a separate clean venv and ran the same suite: **46 passed**, 6.94s. |
| Ruff lint / formatting | All checks passed; 12 backend files already formatted. |
| Strict mypy | No issues in 9 source files. |
| TypeScript | Strict compiler/build passed. |
| Browser acceptance | **5 passed**, 8.1s. Four real-API tests with inference disabled; one explicitly simulated timeout/retry test. |
| Python dependency audit | `pip-audit --local --skip-editable`: no known vulnerabilities reported at audit time. |
| JavaScript dependency audit | `pnpm audit --json`: 0 advisories, all severity counts 0. |
| Local startup | Documented setup/build/start scripts succeeded; `/health` responds. Startup port guard prevents another default-port instance. |
| Restart persistence | Stopped/restarted the real server; browser loaded all 6 previously saved live-model turns and the stored image. |
| Live browser + local inference | Actual browser submitted an uploaded-image question through the API to Ollama; correct red-square/blue-circle answer rendered, no browser page errors. |
| Gemini live API | **Blocked:** owner has no API key. SDK transport tests are not live Gemini verification. |
| Public HTTPS | **Blocked:** owner approved temporary Cloudflare exposure, then automatic approval review rejected download/start with "blocked by policy". No URL/tunnel created; no proxy tests claimed. |
| Glasses / Neural Band | **Not Yet Hardware-Verified.** Owner has hardware; no observed device session. |
| Native glasses camera | **Not implemented.** Phone/desktop uploads are a distinct fallback. |
| GitHub Actions | Workflow prepared; not executed on GitHub because no remote was published. |

One nonfailing upstream warning remains: Starlette deprecates its HTTPX-backed TestClient in favor of HTTPX2. The production provider uses HTTPX and is unaffected by this test-client warning. It is recorded rather than suppressed.

## Real local inference evidence

`scripts/live-smoke.py` generated a white 600×400 test image with a red square at left and a blue circle at right. It sent actual normalized bytes through the running API to `gemma3:4b`, model digest prefix 68ceab7e468a. These were genuine local model outputs, not canned responses.

| Request | Observed answer | Time after warm-up |
|---|---|---|
| Describe image and right-hand shape | "The image shows a red square and a blue circle. The square is on the left, and the circle is on the right. Is the image clear to you?" |2.52s |
| Follow-up: color on the right | "Blue. Is the image clear?" |1.16s |
| Clear image, ask 19+23 | "42." |0.39s |

All three returned HTTP 200. Identical request-ID replays returned identical saved results without adding turns;6 turns persisted and active image context became null after the text-only request. A later real browser question produced "The image shows a red square and a blue circle. Is the image clear?" after server restart.

**Cold-start limitation:** the first vision attempt returned a controlled 504 after 45.34s while GPU/model processing warmed. It was not automatically resent. A subsequent explicit new attempt succeeded as above. These are a few samples, not latency guarantees or OCR/diagram/math accuracy benchmarks. Dense handwriting and real photographs still need representative tests.

Local evidence is in ignored `work/live-local-first-attempt.json`, `work/live-local-smoke.json`, `work/live-browser-proof.json`, `work/live-vision-input.png`, `work/live-interface.png`, `work/live-image-history.png`, and `work/dependency-audit.json`. The synthetic verification conversation remains visible in History. These contain only test content, not private user images or API keys.

## Coverage and corrected findings

Backend checks exercise auth, body limits without Content-Length, content/MIME validation, decompression/pixel limits, image context retention/replacement/clear/delete, conversation isolation, SQLite persistence, bounded history, quotas, timeout/error redaction, provider retry limits, duplicate/conflicting requests, concurrent reservations, pairing single use/expiration/rate limits/revocation and device/admin boundaries. The independent review found malformed Bearer and Origin inputs producing 500; both are now controlled 401/403 regressions. See [security review](security-review.md).

Browser checks exercise invalid login, unconfigured-provider errors without fabricated answers, session restoration, image upload/select/clear/delete, pairing from a separate browser context, admin restrictions, revocation,600px/phone layouts, and explicit user choice before an uncertain request gets a new request ID. Visual inspection confirmed readable real responses and image history in 600×600 captures. Desktop viewport checks do not establish glasses focus/handwriting behavior.

## Quality gates

- **Correctness/reliability:** local text/vision path verified; cloud and wearable gaps labeled. Cold-start timeout remains a disclosed operational limitation.
- **Security:** token/host/origin/body boundaries, safe text rendering and normalized uploads verified within this local single-owner scope. No tool execution or arbitrary URL fetch surface. This is not a public-service penetration test.
- **Maintainability/simplicity:** nine focused backend modules, framework-free TypeScript client, two dependency locks, reproducible setup and source-linked decisions.
- **Performance/cost:** measured warm local latency above; no paid services enabled. Output/history/request limits implemented. Local counts do not guarantee cloud bills.
- **Platform/UX:** implementation follows official web text composer/navigation contracts. Direct capture, Meta distribution and on-device acceptance remain separate gates.
- **Operating boundary:** one server process/worker per database. Multiple users, replicated servers, automated offline expiration and production network DoS defenses are not implemented.

No milestone is labeled fully wearable-complete. The delivered milestone is a verified, editable local application with a documented and partially prepared wearable integration path.
