# Independent security review

Reviewed 2026-10-22 against the local implementation. Scope: request authentication and browser boundaries, image isolation/deletion, concurrent reservation behavior, pairing, provider/tool boundaries, and frontend output rendering. This is a focused engineering review, not an external penetration test or production certification.

## Reproducible checks

Run from the repository root:

```powershell
.venv\Scripts\python.exe -m pytest apps/backend/tests/test_security_review.py -q
.venv\Scripts\python.exe -m ruff check apps/backend/tests/test_security_review.py
```

Final independent result: **10 passed** in 1.17 seconds; Ruff passed. The first run had 9 passes and one malformed-bearer failure; an expanded malformed-Origin case then failed separately. Both were corrected and independently rerun. All model responses in these tests use an explicitly named injected test double. No paid provider requests or real user images are involved.

| Check | Final verified result |
|---|---|
| Private API denies absent credentials and query-string token substitution | Passed |
| Non-ASCII bearer header receives a controlled rejection | Passed after correction |
| Unknown Host and foreign/null/malformed Origin are rejected; accepted responses have no-store, nosniff, CSP and no permissive CORS header | Passed after correction |
| Streamed request without Content-Length cannot bypass the body cap | Passed |
| An image cannot be read, deleted or submitted under another conversation ID | Passed |
| Follow-up requests receive retained image bytes; deletion clears references and later requests receive no image | Passed |
| Paired tokens cannot manage devices; revocation immediately removes access | Passed |
| Concurrent requests reserve only one generation and one unit of request budget in a conversation | Passed |
| In-flight generation blocks concurrent image/conversation mutations | Passed |
| Concurrent pairing redemption issues exactly one token; only its hash is stored | Passed |

## Findings raised during development

**Resolved: malformed bearer header caused HTTP 500.** Sending raw header bytes `authorization: Bearer \xff` to `/api/config` reproduced an uncaught `hmac.compare_digest` error: string comparison does not accept non-ASCII input. The implementation now compares encoded bytes and returns 401. The regression test is `test_malformed_non_ascii_bearer_is_rejected_without_crashing`.

**Resolved: malformed Origin header caused HTTP 500.** Expanding the origin test with `Origin: http://[` reproduced an uncaught URL-parser `ValueError`. The implementation now rejects parsing failures with 403 and disallows paths, queries and fragments in Origin values. The regression case passes.

**SQL placeholder counts were inconsistent.** Static review found extra INSERT placeholders for image and message records. These were reported to the backend owner and corrected before the independent workflow tests ran. Image upload, successful conversation persistence, and deletion subsequently passed through the real SQLite and API layers.

**Retention could clear references during a pending generation.** The initial pruning query selected expired images in busy conversations before excluding their bytes from deletion. The backend owner changed selection to exclude pending conversations as well. Pending mutation guards are tested; a long-duration wall-clock retention test has not been run.

## Inspected controls

User and model text is inserted using `textContent` or text nodes; it is not interpreted as HTML. Browser credentials are kept in session storage, not URL parameters. API keys stay in server settings. Authenticated configuration responses do not return either the admin token or Gemini key. Image previews use authenticated downloads and temporary blob URLs.

Uploads accept genuine JPEG/PNG/WebP data with matching MIME types, bounded bytes and pixels. Images are decoded, orientation-corrected, resized and re-encoded; arbitrary image URLs are not accepted, avoiding a remote-image SSRF surface. HEIC is rejected and the interface gives conversion guidance. Sanitizer-specific cases belong to the backend test suite rather than being duplicated here.

The application has no shell execution, repository mutation or model tool-dispatch endpoint. Instructions embedded in images cannot gain those capabilities through this implementation. The provider system prompt also treats such instructions as untrusted; that prompt is not represented as a complete defense against model persuasion or inaccurate answers.

## Operating limits and remaining verification

- **One local owner:** all paired devices share access to that owner's conversations. This is not a multiuser authorization design. Pair only devices the owner trusts; admin operations require the separate admin token.
- **One server process / worker per database:** startup marks pending requests interrupted for crash recovery. Opening another process against the same database during active work could disrupt that state. Do not deploy multiple workers until process ownership/leases are implemented.
- **Local development boundary:** startup should bind loopback. Remote use requires a deliberate HTTPS exposure decision, explicit host configuration, appropriate proxy handling and additional service hardening. No tunnel or public endpoint was activated by this review.
- Application-level body caps do not provide a complete slow-client/network denial-of-service defense. That belongs to a production proxy and concurrency policy before public hosting.
- Image retention is measured from image creation; conversation retention is measured from last update. Old messages in a conversation kept active can remain longer than the configured number of days. Cleanup runs on startup and relevant API access, not an exact background expiration timer. Deleting stored images removes future image-byte access; earlier descriptive text can remain until the conversation is deleted. Provider-side retention is governed by account terms. SQLite secure deletion cannot guarantee erasure from backups or storage snapshots.
- Cloud credentials, actual Gemini inference, actual Ollama inference, glasses runtime behavior, handwriting and camera delivery remain unverified here. Browser/API tests cannot establish those outcomes.
- Dependency audit and the consolidated test/lint/type-check results are recorded separately in `test-report.md` by the integration owner.

## Final verification

On 2026-10-22, after inspecting both corrections, the independent security suite returned **10 passed, 1 warning** and Ruff returned **All checks passed**. The warning is Starlette's announced deprecation of its HTTPX-backed test client; it did not fail a test and does not represent a live inference check. No outstanding defect was reproduced within this review's bounded local-development scope. The operating limits above still apply.
