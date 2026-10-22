# HTTPS development access

**Current session, 2026-10-22:** The owner manually started Cloudflare. https://session-acquired-elevation-intellectual.trycloudflare.com/ now serves the live app, with the exact hostname allowed locally. Public browser pairing and a real Ollama response passed. https://lensagent.vercel.app opens this URL using a lightweight launch page. Both laptop terminals must stay running. Historical automatic-execution rejection details below do not mean the current user-started tunnel is unavailable. Actual glasses testing remains pending.

No external exposure has been performed. The owner explicitly approved a temporary HTTPS tunnel on 2026-10-22. Automatic approval review then rejected the command to download and start Cloudflare Tunnel with **"blocked by policy"**, without a more specific reason. The command did not run. This is a tool-execution blocker, not missing owner consent; do not ask the owner to approve the same action again. The local server remains bound to `127.0.0.1:8765`; the glasses cannot use that loopback address.

The current [Cloudflare Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) describes temporary HTTPS URLs without an account or domain. It is a development option, with a changing hostname, no uptime guarantee, a 200 in-flight request limit and no SSE support. LensAgent currently uses ordinary HTTP requests. The separately offered email gate requires an interactive browser and has not been tested on glasses.

The following is the documented manual setup for a developer in an environment where tunnel execution is permitted. The owner has already authorized this temporary exposure. Install `cloudflared` from its official distribution and run:

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

This makes the service externally reachable. LensAgent's API still requires a token, while the static connection screen and health endpoint are public. The tunnel service terminates TLS and carries traffic; it is a separate privacy boundary.

Before using the printed hostname, add **that exact hostname**, without scheme, to `.env`:

```dotenv
LENSAGENT_ALLOWED_HOSTS=127.0.0.1,localhost,exact-assigned-hostname.trycloudflare.com
```

Restart the single backend process. Preserve the Host header; trust forwarded HTTPS scheme headers only from the local tunnel/proxy. Uvicorn's local proxy handling must reflect `https` so the same-origin guard accepts browser requests. Verify unauthorized API calls return 401, wrong origins return403, HTTP does not carry credentials, and both pairing and image requests work through the real URL. Those checks remain unexecuted until a tunnel is authorized. Do not use wildcard hosts or disable the guard to work around a failed test.

Install the HTTPS URL on glasses following [hardware validation](hardware-validation.md). Use a pairing code, never an access token in the URL or QR code. Stop the tunnel when testing finishes. Hostname changes require changing the allowed-host setting and glasses URL. Do not open Windows firewall ports for this tunnel.

A production release additionally needs an approved stable host, deployment security review, operational monitoring, privacy policy and relevant Meta distribution requirements. The current single-owner, single-process SQLite application is a local development foundation, not a public multitenant service. Docker, paid hosting, account creation and app publication were not required or performed.
