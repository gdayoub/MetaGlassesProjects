# MetaGlassesProjects

George's projects for Meta glasses.

## Lensly

[Lensly](Lensly/) is a private text and image assistant for Meta Ray-Ban Display, phones and desktops. It uses a FastAPI backend, a TypeScript interface and local Ollama vision inference. The interface includes remembered pairing, chat history, image uploads and a composer attachment menu.

**Home desktop agent: read [START-HERE.md](START-HERE.md) first.** It covers installing the app and vision model, using a named Cloudflare Tunnel with a permanent hostname, automatic startup, credential handling and end-to-end checks.

```powershell
cd Lensly
.\scripts\setup.ps1
.\scripts\start.ps1
```

Setup generates private local configuration. Follow START-HERE before exposing the service publicly. The permanent hostname and home-desktop deployment still need to be configured; this repository is the source and handoff, not a running home server.

## What is included

- `Lensly/`: current application source, lockfiles, tests, model recipes and documentation.
- `START-HERE.md`: complete home-desktop setup and fixed-address handoff.
- `AGENTS.md`: George's private learning-guide requirements for coding agents.
- `.github/workflows/ci.yml`: application checks adapted to this repository layout.

Credentials, personal conversations, uploaded photos, downloaded model weights, generated builds and private `.project-guide.md` files are excluded. Reinstall dependencies and create fresh credentials on each machine. Existing private data can be migrated separately when requested.
