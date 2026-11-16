# HTTPS access for glasses and phones

Meta Ray-Ban Display web apps need a public HTTPS origin. `127.0.0.1` on a
phone or the glasses refers to that device, not the machine running Lensly.
Lensly binds only to loopback and is exposed through a Cloudflare Tunnel, so
no inbound firewall ports are opened.

## Development: quick tunnel

[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
give a temporary HTTPS URL with no account or domain:

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

Add the printed hostname (without scheme) to `.env`, then restart the backend:

```dotenv
LENSAGENT_ALLOWED_HOSTS=127.0.0.1,localhost,<assigned-hostname>.trycloudflare.com
```

The hostname changes every time the tunnel restarts. Because browser storage
is scoped per origin, each new hostname needs to be paired again.

## Stable deployment: named tunnel

For a permanent address, create a **named Cloudflare Tunnel** that routes a
fixed hostname on your own domain to `http://127.0.0.1:8765`. Run
`cloudflared` and Ollama as services so they start with the machine, and set
`LENSAGENT_ALLOWED_HOSTS` to that hostname.

## Security checklist

- The API always requires a bearer token. Only the static connection screen and `/health` are public.
- Use exact hostnames in `LENSAGENT_ALLOWED_HOSTS`, never wildcards. Don't disable the host or origin guard.
- Trust forwarded HTTPS headers only from the local tunnel. Uvicorn must see `https` so the same-origin check passes.
- Pair devices with one-time codes. Never put an access token in a URL or QR code.
- Verify after deploying: unauthenticated API calls return **401**, wrong origins return **403**, and pairing plus an image question both work through the public URL.

Lensly is a single-owner, single-process application backed by SQLite. It is
not designed to be a multi-tenant public service.
