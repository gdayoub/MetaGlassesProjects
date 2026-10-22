# Lensly on iPhone + Ray-Ban Display + Neural Band

Prepared 2026-10-22. The owner confirmed iPhone and successful remembered login on glasses after Display build 3. Lensly build 4 adds the redesigned interface, composer image uploads, previews and saved-image selection. Its updated controls still need on-device navigation checks. Keep the verified Qwen-VL 8B model for lower latency; the 27B model is a separate experiment. Existing installed app entries may still be named LensAgent; open the same URL and reload to see Lensly without changing saved login storage.

## Current readiness

- Local server: `http://127.0.0.1:8765`, laptop only.
- Local API authentication and installed vision-model metadata checks pass.
- Pairing, image history and 600px/phone layouts have automated browser coverage; see the latest test results.
- Public HTTPS: the owner started Cloudflare manually. Current session: https://exciting-digit-tex-hockey.trycloudflare.com/ . Health and API authentication pass; a fresh browser paired and received a real Ollama answer. Keep both laptop terminals running. This address changes when the tunnel is recreated.
- iPhone Safari loads the app and the owner confirms glasses sign-in now works. The redesigned controls and image questions on real glasses still need acceptance checks. The public browser upload-to-Ollama vision flow passes.

Run the read-only local checks from PowerShell:

```powershell
Set-Location 'C:\Users\george\Desktop\LensAgent'
.\.venv\Scripts\python.exe .\scripts\glasses-preflight.py
```

This script does not load a model, generate a pairing code, send an image or publish anything. It writes `work/glasses-preflight.json`. PENDING entries remain work to do even if the command returns success for the local checks.

## Before the session

1. Charge the glasses, band and iPhone. Keep the laptop plugged in and awake for the session. Ollama and LensAgent must remain running on it. No sleep/power settings were changed automatically.
2. Record iOS, Meta AI app, glasses software and band versions. Install available supported updates through their normal interfaces.
3. In Meta AI on the iPhone, locate Developer Mode and the Web Apps connection feature. Meta documentation was rechecked through its public Wearables documentation MCP on 2026-10-22. The Test guide says App Settings > Apps > Web Apps > Connect Web App, enter HTTPS URL, Save. Meta's public toolkit README also describes Devices > Display Glasses settings > App connections > Web apps > Add a web app; labels can differ. Confirm Developer Mode is enabled. Direct docs pages need login, but the public documentation MCP does not. Do not reset or re-pair your hardware merely because a menu differs.
4. Have a public HTTPS origin with a valid certificate before connecting glasses. `127.0.0.1` on the iPhone or glasses refers to that device, not your laptop. The laptop's local HTTP URL is not the glasses deployment URL.

Official sources to open while signed in:
- https://wearables.developer.meta.com/docs/develop/webapps/setup/
- https://wearables.developer.meta.com/docs/develop/webapps/test/
- https://wearables.developer.meta.com/docs/develop/webapps/build/input-and-navigation/

## Once an HTTPS origin is available

Follow `docs/setup/deployment.md` for exact allowed-host and trusted proxy configuration. Do not disable authentication or origin checks to make connectivity work. To check an already-existing origin without sending any token to it:

```powershell
.\.venv\Scripts\python.exe .\scripts\glasses-preflight.py --public-url https://YOUR-EXACT-HOST
```

The optional remote checks verify health and an unauthenticated API rejection. They do not prove authenticated uploads, pairing, forwarded scheme handling or actual glasses operation; perform the following steps through the real URL.

## Test sequence

1. On the laptop, open the HTTPS origin and expand Laptop administrator login and log in with the existing server token from `.env`. Under Settings verify that Ollama selects the expected vision model. Send one short question to warm it if desired; this uses the laptop GPU. Keep model experiments in other terminals idle during the device test to avoid competing for memory.
2. Open the same HTTPS origin in Safari on the iPhone. On the laptop choose Settings > Create glasses pairing code. On iPhone enter it in the first visible pairing-code field. Verify the workspace opens. Codes expire after five minutes and work once; do not generate them long before the session.
3. Create a disposable conversation named "Glasses first test". Ask "Reply with READY" from the iPhone. Record time until answer, whether text fits and whether the question remains available after an error. Check that old/reused pairing codes are rejected using the existing automated coverage; do not disrupt a good session unnecessarily.
4. In Meta AI's Web Apps connection flow, add the HTTPS origin, then launch LensAgent from the glasses app grid. Generate a NEW pairing code on the laptop and redeem it on glasses with **Remember this device** selected (the default). Do not enter the administrator secret on glasses or include it in a URL. The iPhone and glasses need separate one-use codes.
5. On glasses, open History and select "Glasses first test". Activate the question field, handwrite "What is 19 plus 23?", commit it and press Ask once. Record whether the text entry, button activation, waiting state and answer are usable with the band.
6. On iPhone, select the SAME conversation from History. Press **＋ → Upload image** beside the question field, choose a nonsensitive JPEG/PNG/WebP and confirm its preview. HEIC is not accepted; use a compatible image. This picker is a phone/desktop upload, not direct glasses-camera integration.
7. On glasses, open that same conversation from History, then **＋ → Saved images**. Press **Refresh** if the phone just added a photo, select **Use image**, and ask about a visible detail using the red arrow. Ask a follow-up. There is no automatic cross-device live sync. Clear the attachment with **×** when the next question should be text-only.
8. Clear the image and ask a text-only question. Check History, actual text readability, scrolling, focus and native Back behavior. Close and reopen the same installed app without pressing Disconnect. A remembered pairing should restore the workspace and conversation until its seven-day server expiry. Browser storage clearing, app removal or a changed tunnel hostname can require pairing earlier. Record the actual glasses result.

## Results to record

| Check | Pass / Fail / Blocked | Notes |
| --- | --- | --- |
| HTTPS works in iPhone Safari | Owner reports pass | Current Cloudflare origin loads Pair your glasses |
| iPhone pairing and text question | Pending | First and warm request times |
| Glasses launch and pairing | Owner reports login | Exact firmware, entry method and navigation still to record |
| Silent handwriting and one request | Pending | Correct committed text, no duplicate |
| Image selection and correct answer | Pending | Same conversation, refresh needed? |
| Layout and long-answer scrolling | Pending | Real display behavior |
| Exit/reopen and reconnect | Owner reports pass after build 3 | Existing storage keys and seven-day expiry retained in Lensly build 4 |

To end access, use the desktop Settings > Revoke paired devices when you intend to sign out both phone and glasses. Stop the temporary hosting service when the session ends if one is used. An Ollama model that is unloaded with `ollama stop` loads again when an enabled app sends another question; to prevent app inference, disable `OLLAMA_ENABLED` in `.env` and restart LensAgent.


## Blank screen or spinner: Display build 2

The owner reported a blank screen/spinner on the glasses. The cause on hardware is still unconfirmed. Both public URLs returned HTTP 200 in desktop checks; the old Vercel build was intentionally disconnected. A new temporary Vercel redirect now forwards to the live Cloudflare origin. Prefer adding the direct Cloudflare URL to glasses for this session. Reload from the glasses universal menu after a build change, as Meta's troubleshooting guide recommends.

The connection page now puts the supported text pairing field first and hides laptop password login behind a disclosure. It displays Ready / Display build 2 when initialized and a readable loading failure if the module cannot initialize. Storage failures fall back to memory for the active page. No camera integration or successful on-device operation is claimed.

Meta's official QR generator produced outputs/lensagent-add-to-glasses.png in the Codex chat workspace. It encodes the documented fb-viewapp install link for the direct Cloudflare URL, not a secret or a login token. Installation still requires wearer confirmation. On-device pairing and navigation remain pending. Seven browser tests pass, and a fresh 600x600 browser paired through public HTTPS and received 42 for 19 + 23 in 15.5 seconds. The test device and disposable conversation were removed afterward.

Official documentation: https://wearables.developer.meta.com/docs/develop/webapps/troubleshooting/ ; https://wearables.developer.meta.com/docs/develop/webapps/build/input-and-navigation/ ; public toolkit https://github.com/facebook/meta-wearables-webapp . Public docs MCP: https://mcp.developer.meta.com/wearables, search_webapps_docs.

## Remembered login: Display build 3

Reload LensAgent to get the Remember this device checkbox, then pair once with it selected. Earlier session-only logins are not silently converted into saved credentials. The new paired token and its expiry are stored in localStorage under lensagent.remembered-device, scoped to the exact app origin. API requests still validate the token on the server. Settings shows the expiry; Disconnect this browser removes both the saved login and active session. Administrator tokens are never written to persistent storage by the login form.

If browser storage is denied or full, pairing still works for the active page and the app explicitly says it could not remember the login. Expired, malformed or server-revoked saved credentials are cleared. A temporary connection failure does not intentionally erase the saved login. Keep using the same installed URL; clearing app data or replacing the Cloudflare hostname requires a new pairing.

## Lensly build 4 verification

All 11 browser tests pass, including composer upload/preview, correct image selection in API requests, upload-error draft preservation, upload concurrency protection, remembered pairing and 600px layout. A disposable conversation through the public Cloudflare URL uploaded the synthetic red-square/blue-circle picture, received the correct Ollama vision response in 5.95 seconds, restored its image messages after reload, and selected the saved image again. The test conversation and its image were deleted afterward; no existing paired device was changed. The new design was visually inspected at 1365×900, 600×600 and 375×812. These remain browser checks, not claims of native glasses camera access or completed hardware navigation validation.
