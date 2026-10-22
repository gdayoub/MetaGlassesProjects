# Lensly

A private text-and-image assistant designed for Meta Ray-Ban Display, phone and desktop. The owner has confirmed glasses login and remembered sign-in. The interface is now named **Lensly**; the project folder, Python package and configuration prefix remain LensAgent so existing setup and saved logins keep working.

**Local inference works now:** the app uses the installed `lensagent-qwen:8b` vision model through laptop Ollama. Public HTTPS image upload and a real vision answer were verified through the Lensly composer. Gemini is implemented, but a live Gemini key is still needed. Direct glasses camera capture is not implemented.

## Start here on Windows

Open `LensAgent.code-workspace` in VS Code, or open this folder:

```text
C:\Users\george\Desktop\LensAgent
```

In a PowerShell terminal in that folder:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Open **http://127.0.0.1:8765**. Copy the value of `LENSAGENT_API_TOKEN` from your local `.env` file into the connection screen. This is a private application access token, not your Gemini key. Setup creates a random token only when `.env` does not exist, and preserves existing configuration.

Setup uses Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 22+ and pnpm 11. On this machine, it can also find Codex's existing bundled pnpm. The Python environment and locked dependencies live in `.venv`; frontend dependencies live in `apps/web/node_modules`. No Docker or remote service is necessary. If PowerShell blocks local scripts, invoke the needed script with `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1` for that process; no persistent policy change is required.

**Run one server process against this data directory.** Stop it with Ctrl+C before restarting. The server left running by the build is in the background; use `.\scripts\stop.ps1` to stop it. That script only targets this project's Python process running LensAgent. Do not add `--workers`, use reload, or start another copy on a different port against the same SQLite database. The start script rejects an already occupied port. Startup recovers interrupted requests and cannot safely coexist with another active server using that database.

## Use it

1. Choose **Ollama** or a configured **Gemini** provider in Ask. The first configured provider is selected automatically.
2. Write a question. Replies appear as plain text, with recent conversation context retained.
3. Press **＋** beside the question box, then **Upload image** to choose a JPEG, PNG or WebP on your phone/computer. Its thumbnail appears above your draft; press the red arrow to ask about it. You can also paste an image into the question box. **＋ → Saved images** opens images in this chat; select one to use it again. Press the attachment's **×** (Clear image) for a text-only question. The upload button in Images uses the same flow.
4. Use **History** to reopen or delete conversations. An image can be deleted separately. Delete the conversation as well if you want to remove its textual descriptions.
5. In **Settings**, create a one-use pairing code for another browser/device. Leave **Remember this device** selected on the pairing screen to stay signed in after closing the app. The paired token is saved in that browser's local storage, expires after seven days and can be revoked from the administrator browser. Unchecking the option uses session-only storage. Administrator login remains session-only; **Disconnect this browser** erases saved credentials.

All paired devices share **one owner's workspace**. This is not a multiuser service. A second device initially opens a new conversation: use History to choose the shared one. Refresh/reopen the conversation to see another device's changes; there is no live synchronization.

On glasses, use **＋ → Saved images** after uploading from your phone to that same conversation. **Images → Refresh** fetches newly added pictures. The web app does not capture photos from the glasses camera. The centered Lensly header, red-and-black theme and image menu are in `apps/web/index.html`, `style.css` and `src/main.ts`.

## Gemini setup

The [official API-key guide](https://ai.google.dev/gemini-api/docs/api-key) explains creating a key in Google AI Studio. Do this in your own account. Check the project's [pricing](https://ai.google.dev/gemini-api/docs/pricing), [quota](https://ai.google.dev/gemini-api/docs/rate-limits) and [data-use terms](https://ai.google.dev/gemini-api/terms) first. Free-tier eligibility is account-specific; Cloud credits do not automatically cover Gemini API use.

Edit `.env` locally, without posting the key in chat:

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_ENABLED=true
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart the server, select Gemini, and test non-sensitive text and an image. No billing was enabled, key created, or cloud inference performed during this build. Model names are administrator configuration; [AI research](docs/research/ai-models.md) records the current evidence and alternatives. Unpaid Gemini service terms restrict sensitive/confidential submissions and may permit improvement/human review; use the local provider when appropriate.

## Local Ollama

This machine already has Ollama 0.40.6. The build downloaded the 3.4 GB `gemma3:4b` vision model and enabled it only in the private local `.env`. The distributed template keeps both providers disabled.

For another machine with Ollama installed:

```powershell
ollama pull gemma3:4b
```

Then set `OLLAMA_ENABLED=true` and `OLLAMA_MODEL=gemma3:4b` in `.env`, restart LensAgent, and select Ollama. Smaller Gemma3 270m/1b variants do not accept images. See the [model listing and license](https://ollama.com/library/gemma3:4b). The first GPU/model load may exceed the default 45-second timeout. After it warms, start a new explicit attempt; the failed request is not silently replayed. `LENSAGENT_TIMEOUT_SECONDS` supports 1–120 seconds if your hardware needs longer. A small model is a practical fallback, not a substitute for evaluating complex handwriting, math or diagrams.

## Glasses: supported path and limits

For the owner's iPhone, start with the [first device-session guide](docs/setup/glasses-session.md). Run `.\.venv\Scripts\python.exe .\scripts\glasses-preflight.py` from the project root for read-only local readiness checks; PENDING HTTPS/hardware checks still need completion.

Meta documents Display web apps and handwriting in ordinary text controls. The app uses a semantic `textarea`, platform navigation, black background and a tested 600×600 browser layout. **These desktop tests do not verify Neural Band input or on-glasses rendering.**

Your glasses need a reachable HTTPS URL; localhost on this PC is not a glasses deployment. The owner manually started Cloudflare, and the public app now connects to the laptop backend and Ollama. Keep both laptop terminals running. See the [current session guide](docs/setup/glasses-session.md) for the temporary address, pairing and remembered-login checks. A new tunnel hostname has separate browser storage and requires pairing again. [Hardware validation](docs/setup/hardware-validation.md) tracks remaining device tests; [deployment notes](docs/setup/deployment.md) also preserve the earlier automated setup blocker.

Meta reserves glasses camera capture for its native Device Access Toolkit. This build supports phone/desktop image upload and its own image history, not direct glasses capture or arbitrary glasses Gallery access. No native iOS app, Messenger/Instagram bot, WhatsApp integration or Codex execution endpoint is included. See the [architecture decision matrix](docs/architecture/architecture-decision.md) for why these paths were deferred.

## Privacy, limits and reliability

- Data is stored locally in `data/lensagent.sqlite3`, including normalized image bytes. `.env`, database files, generated files and test artifacts are ignored by Git. The database is not encrypted by the application.
- Uploads: 5 MiB, 20 megapixels, JPEG/PNG/WebP only; valid decoded images become metadata-stripped JPEGs with longest side at most 2048 pixels. Convert HEIC first. Original image detail may be reduced.
- Default retention: images expire after seven days; conversations after seven **inactive** days. Cleanup runs at startup and during data API use, not as a background timer. Active conversations can retain older text. Local deletion does not delete provider-held copies or external backups.
- Default request budget: 10/minute, 100 accepted attempts per UTC day, 768 output tokens, 12 historical messages and 16,000 historical characters. Gemini retries explicit 429/503 once; this may cause two upstream attempts per locally counted request. These limits are not a billing guarantee.
- Saved request IDs prevent duplicate generation. Network timeout/interruption may have an unknown provider outcome. Retrying the same logical request retrieves its saved result; an explicit new attempt may incur another provider call.
- Paired tokens cannot administer devices; authenticated devices otherwise share full workspace access. No external image URLs, user-selected server paths, executable model tools, shell access or remote agent commands are accepted.

## Develop and verify

```powershell
.\scripts\check.ps1
.venv\Scripts\python.exe -m pip_audit --local --skip-editable
```

Browser tests use Microsoft Edge on Windows, or Playwright Chromium on Linux:

```powershell
cd apps\web
pnpm test
```

If pnpm is not on PATH, the bundled executable used by `scripts/build-web.ps1` can run `--dir apps/web test`. The tests launch an isolated real API with both providers disabled and temporary data. They cannot spend API credits. Backend tests use explicit inference test doubles and mocked provider transports.

The optional `python scripts/live-smoke.py` runs genuine Ollama text/vision requests against a running server on port 8765, using a generated red-square/blue-circle image. It saves a synthetic conversation plus evidence under `work/`; it is not part of the offline suite. [Test report](docs/quality/test-report.md) separates automated, live-local, live-Gemini and hardware evidence.

Frontend source: `apps/web/src/main.ts`, `index.html`, `style.css`; rebuild with `scripts/build-web.ps1` after edits. Backend entry point: `lensagent.api:create_app`. New providers implement the small contract in `providers.py`. Extend transports separately from inference and persistence; do not give model output command execution rights.

## Troubleshooting

| Symptom | Next step |
|---|---|
| Invalid configuration at startup | Run setup; check `.env` names and an access token at least 32 characters long. Error output deliberately omits values. |
| Gemini is not enabled / no response | Add the key locally, enable Gemini and restart; inspect your account's model access/quota. |
| Ollama timeout | Wait for model warm-up, then make an explicit new attempt. Check `ollama ps`; increase the timeout within its bound if needed. |
| Stopped model loads again | An enabled Ollama provider loads its model on the next question. To prevent app inference, set `OLLAMA_ENABLED=false` in `.env` and restart LensAgent. |
| Image refused | Convert HEIC to JPEG, reduce file size/dimensions and use one frame. |
| 401 after expiry or device revocation | Use a new pairing code. For future app exits, leave Remember this device selected. Administrator login remains session-only. |
| 403 through a tunnel | Check exact allowed host, same-origin URL and trusted proxy HTTPS handling. Do not disable authentication. |
| Text seen on another device is stale | Reopen the shared conversation from History or refresh. |
| Port 8765 in use | Stop the existing LensAgent process before restarting. Do not run two servers on one database. |

See [system overview](docs/architecture/system-overview.md), [engineering decisions](docs/decisions/engineering-decisions.md), [project status](docs/project-status.md) and the source-linked [research](docs/research/meta-platform.md).
