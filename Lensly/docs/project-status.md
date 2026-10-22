# Project status — 2026-10-22

**Delivered:** permanent Desktop project, local Git source, locked Python/TypeScript setup, authenticated web/API, real Gemini/Ollama adapters, SQLite conversations and image history, context clearing/deletion, device pairing/revocation, usage limits and error handling. Research covers Meta, messaging, models and 8 relevant repositories; architecture and hardware checklists are included.

**Verified:** 46 backend tests, 5 browser tests, lint/types/build, separate clean Python environment, dependency audits, actual local text+image inference and browser display, saved context across a server restart. See [test report](quality/test-report.md).

**Current local state:** application running at http://127.0.0.1:8765 with Ollama `lensagent-qwen:8b` enabled in private `.env`. This is Qwen3-VL 8B Instruct Abliterated v2 Q4_K_M with its Q8 vision projector. Gemini remains disabled. Local access token is in `.env`; it is not printed or committed. The interface and setup guide are available in the Desktop folder. No remote Git repository or public site exists.

**Owner inputs:** owner has glasses and Neural Band, but no Gemini key. Owner explicitly approved a temporary HTTPS tunnel. Automatic approval review rejected the Cloudflare download/start command with "blocked by policy" before execution; no more specific reason was supplied. Consent remains recorded; asking for it again is unnecessary.

**Remaining:** a permitted HTTPS execution route and actual device acceptance session; optional Gemini key/live validation; native iPhone camera companion and supported handoff are not implemented. No macOS/signing environment was identified. No claims of direct glasses capture or handwriting validation are made.

**Known local limit:** first model load timed out at 45s; warm vision answers subsequently took 2.52s and 1.16s. The UI preserves unknown outcomes and offers an explicit new attempt. One backend process and one owner's shared data are supported.

**Next:** resolve the HTTPS execution blocker, follow `docs/setup/hardware-validation.md` with the owner's glasses, then implement a native capture spike only when a supported build/signing environment and validated handoff are available. Future coding-agent access must preserve explicit permission boundaries.

## Owner preference update — 2026-10-22

The owner objected to local model execution. Gemma was stopped and `OLLAMA_ENABLED=false` applied to the private configuration; the backend was restarted. No model remains loaded in Ollama. The approximately 3.4GB download remains on disk. Earlier enabled/running statements above describe the prior build-validation state. Do not download, enable or run a local model again without explicit owner approval.

## Qwen setup authorized and verified — 2026-10-22

The owner clarified that they enjoy local AI and want to learn the setup, then explicitly authorized downloading Qwen and connecting it to LensAgent. This supersedes the disabled-provider state above for this model. Downloaded `hf.co/prithivMLmods/Qwen3-VL-8B-Instruct-abliterated-v2-GGUF:Q4_K_M` with its matching Q8 projector (~5.8 GB total) and created local alias `lensagent-qwen:8b`, model ID `d2d7b3e01eb9`. Ollama reports vision capability. Gemma remains on disk as an alternative.

Made context configurable through `OLLAMA_CONTEXT_LENGTH` (default 4096, supported 2048-32768) instead of hardcoding 8192. Private settings enable Ollama with context 4096, maximum output 256 tokens and a 90-second timeout. Login credentials were preserved. The backend was restarted and its configuration endpoint confirmed the selected model enabled.

Validation: all 46 backend tests, Ruff and mypy pass. Authenticated live image inference correctly identified a red square left and blue circle right (25.62 seconds including loading), answered the image follow-up (1.62 seconds), and answered a text-only math question (0.45 seconds). `ollama ps` reported 100% GPU at context 4096. The live browser loaded saved messages, submitted an image question, and displayed the correct answer without JavaScript errors. These are functional smoke tests, not comparative quality benchmarks or glasses hardware validation.

The owner's hidden, Git-ignored `.project-guide.md` contains the beginner walkthrough, file map, exact download/alias/settings/restart commands, hardware observations and troubleshooting steps. Local evidence is in `work/live-local-smoke.json`, `work/live-browser-proof.json` and `work/live-interface.png`. The app remains local; no tunnel or public endpoint was created.

## Separate 14B terminal model — 2026-10-22

Owner requested a 14B experiment. Installed the text-only Huihui-Qwen3-14B-abliterated-v2 Q4_K_M from Hugging Face (~9.0 GB) as `qwen14`. LensAgent's configured 8B vision model is unchanged. Added `models/Qwen14.Modelfile` with the official Ollama Qwen3 chat template, stop tokens, context 4096 and no fixed generation cap. This fixes the upstream import's raw-prompt template, which leaked thinking markers during initial testing. Recommended direct terminal command: `ollama run qwen14 --think=false`.

Two short warm explanation tests took 5.92 and 7.82 seconds, generating at 13.73 and 13.65 tokens/second with 38% CPU / 62% GPU placement. The same prompts on 8B took 1.78 and 1.91 seconds at about 50 tokens/second. This verifies functional text generation and the speed tradeoff, not superior general intelligence. Full setup, limitations and benchmark locations are in the private hidden project guide. No app provider change or public deployment occurred.

## Larger vision experiment and iPhone/glasses preparation — 2026-10-22

Installed Gemma 3 27B Abliterated Q4_K_M plus its matching vision projector (~17.4 GB) as `gemma27-vision`, with reproducible recipe `models/Gemma27-Vision.Modelfile`. Direct local synthetic image tests passed: shape identification and receipt OCR (lamp $24, cable $8, total $32). First image including load took 37.29s; warm receipt 9.65s; text 8.48s. Generation was 4.6-5.1 tokens/s at context 4096, with 72% CPU / 28% GPU placement reported by Ollama. CLI image input also returned the correct total. These are small smoke tests, not general quality benchmarks.

LensAgent remains on the faster Qwen-VL 8B. Added an explanatory Settings note for on-demand model loading: `ollama stop` unloads the model; enabled app requests load it again. Built the frontend and passed all five browser tests, including pairing/revocation, images and small-display layout. Added `scripts/benchmark-vision.py`, a synthetic-image benchmark, and `scripts/glasses-preflight.py`, a read-only local/optional-existing-HTTPS readiness check. Both scripts pass Ruff; local preflight passes and an HTTP-only public URL is correctly rejected. Reports and measurements are in ignored `work/`.

Owner confirmed iPhone. Added `docs/setup/glasses-session.md` with Safari-first checks, separate pairing codes, handwriting and same-conversation image flow, and a hardware results table. Meta's official setup/test pages now require login in this environment; previously recorded menu/version details are explicitly marked for confirmation. HTTPS and actual device tests remain pending. The earlier Cloudflare automatic-review rejection is unchanged; no tunnel was retried or bypassed, no public URL was created, and no direct glasses-camera capture was implemented. The hidden project guide contains the complete walkthrough and results.

Final live browser check passed on Qwen-VL 8B: loaded eight persisted turns and returned the correct red-square/blue-circle answer without browser errors. The verification helper now accepts an already-selected image. Gemma 27B was unloaded after testing; Ollama confirmed the app's 8B model loaded entirely on GPU.

## Vercel public interface — 2026-10-22

Owner requested publication through the Vercel plugin and confirmed Ollama should remain local. Published the static interface at https://lensagent.vercel.app (production deployment dpl_CeJp1qJ4jkRLBYNEzpyASXNsBmFa, project prj_4VeY8MZOLgnh7UWue4uf1eczZTxk, team gdayoubs-projects). Vercel reports READY. Added apps/web/scripts/build-vercel.mjs to create an explicit public asset bundle with an offline-backend state and disabled login/pairing fields. The local build remains unchanged. No private files or backend were deployed; no tunnel was attempted. The prior blanket statement that no publication occurred is superseded only for this static frontend.

Validation: frontend build passes; live browser HTTP 200 with no script errors; both credential and pairing forms disabled; private .env, .project-guide.md and database URLs return 404. Laptop backend connectivity, real pairing and inference at this public URL remain incomplete. The previous Cloudflare automatic-review rejection is unresolved. Public HTTPS alone does not make local Ollama accessible.

## Meta Display loading investigation — 2026-10-22

Owner manually established Cloudflare; its public origin now passes health and unauthenticated-API rejection. Fresh public-browser pairing and a real Ollama answer passed (19 + 23 -> 42, 15.5 seconds). Evidence: work/public-paired-proof.json. This supersedes earlier statements that HTTPS was unavailable. The owner reports a spinner on glasses; the hardware cause remains unconfirmed.

Consulted Meta's official public Wearables docs MCP and toolkit repository. Paired-code entry is now the first control; laptop password login is in a separate disclosure. Added storage-denied fallback and visible startup failure handling. All seven browser tests pass. Vercel production deployment dpl_DF8Ena1NAkcUVAcCzBnbAnGfd1RB redirects to the user's current Cloudflare origin; no server/model secrets are deployed. Generated the official-format Meta install QR for the exact direct URL. Actual glasses launch, pairing, and navigation still require wearer confirmation.

### Persistent spinner diagnostic

The owner still sees the glasses loader after Display build 2. Public HTML, assets and health remain reachable from desktop; the hardware cause is unresolved. A minimal separate LensAgent Check page is now at /display-check.html on the active Cloudflare origin. It renders DISPLAY CHECK A with JavaScript disabled, needs no auth/inference, and has under 1 KB of HTML+CSS. Its Meta-format QR is in the chat outputs folder. Awaiting iPhone Safari and on-glasses diagnostic results before changing more application behavior.

### Direct Vercel diagnostic — 2026-10-22

Owner confirmed glasses stay on the app icon then show "app not loading"; iPhone Safari loads the live Cloudflare app. Published the minimal check directly at https://lensagent.vercel.app/display-check.html (dpl_8BWXR2EDFkdpErALg4nkSv7PfhNM, READY). Verified public HTTP 200 and rendering with JavaScript disabled, no redirects and no non-Vercel asset requests. Awaiting on-device comparison. This diagnostic does not provide AI; the existing homepage still opens Cloudflare. No known hardware root cause yet.

## Remember paired-device login — Display build 3, 2026-10-22

The owner now reports login on glasses, followed by losing login after exit/reopen. This supersedes the launch-blocked state without proving what resolved the earlier spinner. Added Remember this device, enabled by default on pairing. Paired credentials and their existing seven-day expiry persist in localStorage; administrator credentials remain session-only. Disconnect and API 401 clear saved credentials. Expired/malformed records are discarded before restoration; blocked storage yields a visible warning and usable active session. A fresh pairing is needed to opt earlier session-only logins into persistence.

Validation: frontend build and all 10 browser tests pass. Tests cover a fresh browser context carrying only persistent storage, conversation restoration, sign-out, revocation, opt-out, damaged/expired records, denied storage and the existing UI flows. The real test API uses a temporary database with inference disabled. Public HTML, main.js, stylesheet and health return 200 with no-store headers; public HTML/JavaScript contain the new checkbox and Display build 3. No backend restart, real-device revocation, live pairing-code generation or model invocation was needed. On-glasses remembered login remains for the owner to confirm. Updated setup documentation and the Hidden, Git-ignored personal project guide.

## Lensly redesign and composer images — 2026-10-22

Owner confirms remembered sign-in works and requested a centered Lensly identity, a polished red-and-black space-inspired UI and ChatGPT-style image attachment controls. Lensly build 4 replaces the corner brand/status badges and framed panels with a centered wordmark, restrained navigation, an orbital empty state and a compact composer. Auth state appears in Settings. Project paths, server configuration, the active tunnel, model choice and saved authentication keys are unchanged.

The composer plus button opens Upload image and Saved images. Uploads return to the draft with a thumbnail; existing pictures can be selected again. User messages now show the image sent with them, including after reload. The × control removes image context for the next question. Upload validation/errors preserve the draft; inference, view changes and new chats are disabled during an upload to prevent sending before the image is ready or attaching to the wrong chat. Image blob URLs are authenticated, reused within a conversation and released when leaving it. A version check prevents overlapping library refreshes from appending stale results. Images has a Refresh button for the phone-upload/glasses-selection flow. Direct glasses camera capture remains unimplemented.

Verification: frontend typecheck/build and all 11 browser tests passed. A real public HTTPS browser uploaded a disposable synthetic image and received the correct local Ollama answer, 'A red square and a blue circle on a white background', in 5.95 seconds. Restored message thumbnails, saved-image selection and phone layout passed with no browser exceptions. Screenshots were inspected at desktop, 600×600 and phone sizes. The disposable conversation/image were removed; existing user data and paired devices were preserved. Evidence: work/lensly-live-proof.json; output previews in the Codex chat's outputs directory. Hidden guide and setup instructions explain the new controls and customization points.

## Temporary tunnel recovery — 2026-10-22

The earlier trycloudflare.com hostname expired with DNS NXDOMAIN while the laptop backend remained healthy. The owner manually restarted Cloudflare and supplied https://exciting-digit-tex-hockey.trycloudflare.com . Its readiness check passes. Updated the exact allowed hostname in private configuration and restarted the single backend; all other dotenv values were preserved. The app server now runs in the background and can be stopped with scripts/stop.ps1. The owner's Cloudflare terminal must remain running.

Published the corrected public launch page to the existing production project: dpl_5ezbF5RRFzz53HUjwjvW2Gwhahp3, READY, alias https://lensagent.vercel.app/ . A fresh browser reached the new exact origin, loaded Lensly build 4 and authenticated successfully. Public health 200, unauthenticated API 401, foreign Origin 403; no browser errors or inference calls. Only the disposable test conversation was removed. Existing devices and conversation data were preserved. Evidence: work/tunnel-recovery-proof.json. Glasses entries and remembered logins are origin-specific: update the saved app URL and pair again once. Fresh install QR: the chat output lensly-add-to-glasses.png. Updated the current setup guide and private learning guide.
