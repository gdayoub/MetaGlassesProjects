# Lensly home desktop setup and permanent address

George's request: move this working glasses assistant to his home desktop and give it a fixed HTTPS address so restarting the tunnel does not require editing the glasses Web App URL and pairing again. Finish installation and verification on the home computer. Preserve the working Lensly interface and explain the setup as you go.

## Start with the repository

The repository is `https://github.com/gdayoub/MetaGlassesProjects`, intended to be private. Read the root `AGENTS.md`. The application lives in `Lensly/`; run application commands from that directory. If this file is being used with the original laptop project instead, that project's root is `C:\Users\george\Desktop\LensAgent`.

This is a source snapshot with the latest working changes, including changes that had not been committed in the laptop's original repository. It contains no working credentials, conversations, uploaded photos, installed model weights, virtual environments or private learning guide. Reinstall dependencies and create local configuration on the home machine. Do not assume a laptop path exists there.

## Architecture and current behavior

The browser runs vanilla TypeScript compiled to static files. FastAPI serves both the interface and `/api` from one origin on `127.0.0.1:8765`. SQLite stores the single owner's data. The backend calls Ollama locally at `127.0.0.1:11434`. Keep both services on loopback. A Cloudflare connector publishes only the Lensly backend over HTTPS.

The visible product name is **Lensly**, build 4. Python modules, folder names and environment prefixes remain `lensagent`/`LENSAGENT_`. Pairing uses one-time eight-digit codes created by the administrator. Remembered paired credentials use `lensagent.remembered-device` in localStorage and survive ordinary app exits. User messages and the composer show attached images. The plus menu offers Upload image and Saved images. On glasses, pictures can be selected after uploading from a phone into the same conversation. Direct glasses camera capture is not implemented.

The current laptop is still live behind a temporary tunnel. Do not stop or alter it just to prepare the desktop. Its current temporary origin is `https://exciting-digit-tex-hockey.trycloudflare.com/`. The older `session-acquired-elevation-intellectual.trycloudflare.com` address expired and must not be reused. `https://lensagent.vercel.app/` is a static launch page forwarding to the temporary origin; it does not run Python or Ollama. Historical notes elsewhere describe earlier states; use this handoff and inspect actual configuration.

## Inspect the home machine

Identify its OS, GPU and dedicated VRAM, RAM, free disk, installed tools and occupied ports. Windows commands are the primary path below; adapt to the actual OS rather than assuming it is Windows. Inspect existing Ollama and cloudflared processes/services before adding any. The existing laptop's 8B vision model fit an 8 GB GPU; the 27B model was substantially slower. Home hardware has not been inspected, so do not promise a model size or speed.

Ask George only for missing account/domain access and choices that require him. Use already-connected accounts where available. Ask him to authenticate through the provider's normal UI; never request account passwords, API keys or tunnel tokens in chat. Do not buy a domain or change billing without his explicit approval of the actual purchase.

## Install and start locally

Install Python 3.12, uv, Node.js 22 or newer, pnpm 11, Ollama and cloudflared from their official distributions. The lockfiles record Python and web dependencies. Prefer the project's setup script over manually selecting dependency versions.

From `Lensly/` in PowerShell:

```powershell
.\scripts\setup.ps1
```

This creates `.venv`, installs dependencies, builds the frontend, and creates `.env` with a fresh random administrator token only if `.env` does not already exist. Keep that token private. The supplied template initially disables model providers.

Install the laptop's vision model and alias if the inspected home machine has suitable resources:

```powershell
ollama pull hf.co/prithivMLmods/Qwen3-VL-8B-Instruct-abliterated-v2-GGUF:Q4_K_M
ollama create lensagent-qwen:8b -f .\models\Qwen8-Vision.Modelfile
ollama show lensagent-qwen:8b
```

The portable recipe derives from the installed laptop alias's ChatML template and stop tokens. The upstream import must provide its matching vision projector. Verify vision capability and actual synthetic-image inference on the desktop; the new recipe was not downloaded or rebuilt on the laptop as part of this handoff. If the upstream import changes or fails, investigate the official Ollama import format and that model repository rather than silently substituting a text-only model. Other 14B/27B recipes are optional experiments, not the initial deployment target.

Edit these non-secret settings in the new local `.env`, preserving the generated administrator token:

```dotenv
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=lensagent-qwen:8b
OLLAMA_CONTEXT_LENGTH=4096
LENSAGENT_MAX_OUTPUT_TOKENS=256
LENSAGENT_TIMEOUT_SECONDS=90
GEMINI_ENABLED=false
```

Run `.\scripts\start.ps1` and test `http://127.0.0.1:8765/`. Run one backend process per data directory. Stop it with Ctrl+C in its foreground terminal or `.\scripts\stop.ps1` before restarting. Do not add multiple Uvicorn workers or a second backend against the same SQLite file.

## Give the glasses one fixed address

Use a **named, remotely managed Cloudflare Tunnel** and a fixed public hostname on a domain George owns and controls through Cloudflare. For example, `lensly.example.com` is a placeholder, not an address George owns. If no domain is available, report that concrete dependency and help him select a domain separately. A Quick Tunnel with a changing `trycloudflare.com` URL is not the requested permanent setup. Repointing the Vercel redirect alone does not preserve browser storage when its destination changes.

In the current Cloudflare dashboard, create the named tunnel and install its Windows connector on the home desktop using the provider-generated installation command. Keep the tunnel token out of source files, chat, screenshots, published logs and shell transcripts. Use the official Windows service installation path where possible so closing a terminal does not stop the connector. Inspect any pre-existing cloudflared service before changing it. Do not run a duplicate connector on the laptop against a different local database; requests could be distributed between inconsistent backends.

Add a published application route:

```text
Public hostname: the agreed permanent hostname
Local service:  http://127.0.0.1:8765
```

Publish the entire app and API at that hostname. Preserve the original public Host and the forwarded HTTPS scheme. Do not override the Host to localhost as a workaround. Add exactly that permanent hostname to `LENSAGENT_ALLOWED_HOSTS` in `.env`, together with loopback names, and restart the single backend. Do not use wildcard hosts or disable RequestGuard, authentication or same-origin checks. Leave Ollama's port private. No router port forwarding is needed.

Keep existing unrelated DNS records, including mail records. Do not introduce a Cloudflare Access interstitial without testing its login flow on the actual glasses; Lensly already requires its administrator or paired-device credential for private APIs. Follow the installed tool and current official dashboard documentation if labels have changed.

Keep the named tunnel and DNS hostname across desktop restarts. Restart the connector; do not delete and recreate a Quick Tunnel to recover service. If George later moves computers, move the connector/backend behind this same hostname while preventing simultaneous inconsistent backends.

## Keep all three services available

Configure the named cloudflared connector, Lensly backend and Ollama to restart automatically under an appropriate Windows account. A default Ollama tray app is tied to its user's login session. A startup task running as SYSTEM will not automatically see another user's Ollama model directory or environment.

For the backend use the absolute project `.venv\Scripts\python.exe` with `-m uvicorn lensagent.api:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log` and the application root as working directory. Use one instance, restart on failure, and local operational logs that do not print credentials. Configure Ollama under the account that owns the installed models, or explicitly configure and secure its model directory for the chosen service identity. Use official service/Task Scheduler facilities; avoid visible recurring terminal windows.

Confirm with George whether operation before Windows sign-in is required and use the corresponding service or task account. If account credentials are required, let him enter them directly in Windows. Test the actual boot/sign-in behavior rather than calling a logon-only setup unattended hosting. The desktop must stay powered and network-connected while the glasses are used. Review sleep settings with George before changing them. Do not change unrelated power, firewall, remote-access or account settings.

## Pair once at the fixed origin and explain expiry

Once the permanent HTTPS origin passes the checks below, update the saved glasses Web App entry to that direct origin. Create a new one-use pairing code from the trusted administrator browser and redeem it on glasses with Remember this device selected. Tokens must never be embedded in the URL or QR code. Because the origin changes once during this move, the glasses must pair once again. After that, ordinary backend, tunnel and desktop restarts must keep the same hostname and stored device credential.

Current server-issued device credentials expire after **seven days**. A fixed hostname fixes restart-induced pairing; it does not make that credential immortal. Explain the existing expiry to George. If he wants longer-lived trusted glasses sessions, implement a configurable, revocable device lifetime with server validation, matching UI copy and meaningful expiry/revocation tests, after resolving the desired duration with him. Do not silently remove expiry or persist the unrestricted administrator token on glasses.

Leave the current laptop's data untouched. This source transfer starts with fresh desktop data and credentials. If George wants existing conversations/photos migrated, prepare a private backup and migration separately. Never commit `.env` or `data/lensagent.sqlite3` to transport them. A consistent SQLite migration requires stopping the source backend or using SQLite's online backup API; do not copy a live database arbitrarily.

## Update the convenience link after the permanent origin works

The existing Vercel project is `lensagent`, project ID `prj_4VeY8MZOLgnh7UWue4uf1eczZTxk`, under team `gdayoubs-projects` (`team_i0svKVi4T5nTE1I9QsV29IEH`). Latest laptop recovery deployment: `dpl_5ezbF5RRFzz53HUjwjvW2Gwhahp3`. Confirm the actual connected account/project before any deployment.

When authorized account access is available, build from `Lensly/apps/web`:

```powershell
pnpm run build
node scripts/build-vercel.mjs https://THE-REAL-PERMANENT-HOST
```

Deploy only the generated public allowlist in `dist-vercel` to the existing project, replacing the temporary destination. The deploy API previously omitted redirect configuration, so the generated HTML meta-refresh/link fallback also matters. Verify the final browser URL. Do not publish the repository root or private configuration. Install the direct permanent origin on glasses even if Vercel remains a convenient launch link.

## Verify before declaring completion

Run `scripts/check.ps1` from the application root for backend lint, types, tests and web build. Run `pnpm test` from `apps/web` for browser tests. Tests use an isolated API on port 8766 with inference disabled. Adapt browser installation for the actual OS; the Windows suite uses installed Edge. Existing laptop evidence is 11 passing browser tests, plus real public vision inference. These are a baseline, not proof of a home installation.

Verify the complete home setup:

- Local and permanent public `/health` return 200; unauthenticated `/api/config` returns 401.
- Valid administrator/paired authentication works through the permanent origin; an unrelated Origin is rejected with 403.
- The real home Ollama model answers a text question and identifies a generated nonsensitive picture uploaded through the plus menu. Confirm the selected model, image bytes and actual returned answer, rather than relying only on model metadata.
- Phone upload and saved-image selection refer to the same conversation. Clear image, history, deletion, error recovery and device revocation still work.
- Close and reopen the glasses app. Restart the backend and tunnel separately. Reboot the desktop using the configured startup account. Recheck the same exact hostname and remembered login after each, within the credential lifetime.
- Perform an actual glasses check with George. Desktop-browser success alone does not establish band navigation, display readability or device persistence.

Keep disposable checks separate from personal conversations and remove only objects created by the test. Record the real outcome and any remaining account/domain/hardware blockers without claiming the permanent setup already exists.

## Maintain George's private learning guide

Create and maintain a Hidden `.project-guide.md` at the repository root and application root on the home machine. Ignore these files in Git and verify with `git check-ignore -v`; never force-add or commit them. Preserve George's notes. Explain the actual home installation paths, architecture, customization points, permanent hostname, startup tasks/services and identities, model directory, credential locations without values, backup/recovery procedure and setup/start/stop/build/test commands. Show him its exact path and how to open it in Notepad.

Important files: `apps/web/index.html`, `style.css`, `src/main.ts`; `apps/backend/src/lensagent/config.py`, `providers.py` (including the app's system prompt), `security.py`, `storage.py`, `images.py`; `models/Qwen8-Vision.Modelfile`; `scripts/setup.ps1`, `start.ps1`, `stop.ps1`, `build-web.ps1`, `check.ps1`; `apps/web/tests/flows.spec.ts`.

Finish with the final permanent URL, actual service/task names, startup/recovery commands, verification results and the glasses pairing step. Do not leave George with another changing tunnel URL.

## Official references

- Cloudflare dashboard tunnel setup: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/
- Cloudflare hostname routing: https://developers.cloudflare.com/tunnel/concepts/routing/
- Cloudflare token handling: https://developers.cloudflare.com/tunnel/reference/tunnel-tokens/
- Cloudflare Quick Tunnel limits: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
- Ollama on Windows and model locations: https://docs.ollama.com/windows
- Meta Web Apps setup: https://wearables.developer.meta.com/docs/develop/webapps/setup/
- Meta Web Apps testing: https://wearables.developer.meta.com/docs/develop/webapps/test/

References checked 2026-10-22; verify current install commands on the destination machine.
