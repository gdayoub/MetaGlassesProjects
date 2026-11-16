# Lensly: setup and usage guide

Lensly is a private text-and-image AI assistant for **Meta Ray-Ban Display**
glasses, phones and desktops. A FastAPI backend serves a TypeScript web
client and routes questions to a **local Ollama vision model** or, optionally,
**Google Gemini**.

> The Python package and configuration prefix are named `lensagent` /
> `LENSAGENT_`, which was the project's original name.

## Requirements

Python 3.12 · [uv](https://docs.astral.sh/uv/) · Node.js 22+ · pnpm 11 ·
[Ollama](https://ollama.com) (for local inference). No Docker is needed.

## Quick start (Windows / PowerShell)

```powershell
.\scripts\setup.ps1     # creates .venv, installs locked deps, builds the web app, writes .env
.\scripts\start.ps1     # serves the app + API on http://127.0.0.1:8765
```

Open **http://127.0.0.1:8765** and sign in with the `LENSAGENT_API_TOKEN`
from your local `.env`. Setup generates a random token only if `.env` doesn't
exist yet. Stop the server with `.\scripts\stop.ps1`.

### Enable a model

**Local (Ollama):** pull a vision model and enable it in `.env`:

```powershell
ollama pull gemma3:4b
```

```dotenv
OLLAMA_ENABLED=true
OLLAMA_MODEL=gemma3:4b
```

The `models/` folder has Modelfile recipes for larger vision models, such as
Qwen3-VL 8B, which fits an 8 GB GPU.

**Cloud (Gemini, optional):** create a key in Google AI Studio and set:

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_ENABLED=true
```

Both providers are **disabled by default** in `.env.example`.

## Using it

1. **Ask:** type a question, or press **＋ → Upload image** to ask about a JPEG, PNG or WebP. You can also paste an image.
2. **Saved images:** reuse any image already uploaded to the conversation. On the glasses, upload from your phone first, then pick it here.
3. **History:** reopen or delete conversations and images.
4. **Settings → pairing code:** create a one-time 8-digit code to connect another device. With *Remember this device* checked, the paired token persists for 7 days and can be revoked from the admin browser.

## On the glasses

Ray-Ban Display web apps need a public **HTTPS** origin. See
[docs/setup/deployment.md](docs/setup/deployment.md) for running Lensly
behind a Cloudflare Tunnel. Add the HTTPS URL in the Meta AI app's Web Apps
settings, launch Lensly from the glasses, and pair with a code. Text input
uses the glasses' system composer (Neural Band handwriting or dictation).

Lensly does not capture photos directly from the glasses camera. Meta
reserves that for its native Device Access Toolkit. Images are uploaded from
a phone or desktop instead (see the
[architecture decision](docs/architecture/architecture-decision.md)).

## Privacy and limits

- All data stays local in SQLite (`data/lensagent.sqlite3`). `.env`, databases and build output are git-ignored.
- Uploads are limited to 5 MiB and 20 MP, then re-encoded as metadata-stripped JPEGs with the longest side at most 2048 px.
- Images expire after 7 days. Conversations expire after 7 days of inactivity.
- Default limits are 10 requests per minute, 100 per day and 768 output tokens. Each request includes the 12 most recent messages as context.
- Request IDs make retries idempotent: re-sending the same request returns the saved result instead of calling the model again.
- Model output is rendered as plain text and cannot execute commands. There is no shell or tool access.

## Development

```powershell
.\scripts\check.ps1                 # ruff, strict mypy, pytest, frontend build
cd apps\web; pnpm test              # Playwright end-to-end tests
python scripts\live-smoke.py        # optional: real Ollama text + vision round trip
```

| Path | Purpose |
|---|---|
| `apps/backend/src/lensagent/api.py` | FastAPI app, routes, auth boundary |
| `apps/backend/src/lensagent/providers.py` | Provider interface + Ollama / Gemini implementations |
| `apps/backend/src/lensagent/security.py` | Tokens, pairing, host/origin checks |
| `apps/backend/src/lensagent/images.py` | Image validation and normalization |
| `apps/backend/src/lensagent/storage.py` | SQLite persistence, retention, request dedup |
| `apps/web/src/main.ts` | Web client (vanilla TypeScript) |

To add a model provider, implement the small interface in `providers.py`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Invalid configuration at startup | Re-run setup. The access token must be at least 32 characters. |
| Ollama timeout on first question | The model is still loading into memory. Wait a moment and ask again, or raise `LENSAGENT_TIMEOUT_SECONDS` (max 120). |
| Image refused | Convert HEIC to JPEG, or reduce the file size or dimensions. |
| 401 on a paired device | The token expired or was revoked. Pair again with a new code. |
| 403 through a tunnel | Add the exact hostname to `LENSAGENT_ALLOWED_HOSTS`. |
| Port 8765 in use | Run `.\scripts\stop.ps1`. Only one server may use the database at a time. |

## Further reading

[System overview](docs/architecture/system-overview.md) ·
[Engineering decisions](docs/decisions/engineering-decisions.md) ·
[Security review](docs/quality/security-review.md) ·
[Test report](docs/quality/test-report.md) ·
[Meta platform research](docs/research/meta-platform.md) ·
[Model research](docs/research/ai-models.md)
