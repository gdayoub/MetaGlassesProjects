# Hardware validation

For the owner's confirmed iPhone setup, start with [the first-session guide](glasses-session.md) and run `scripts/glasses-preflight.py`. Current platform guidance was retrieved using Meta's public Wearables documentation MCP on 2026-10-22. Direct documentation pages still require login. Confirm hardware versions in the phone app; desktop validation does not replace on-device testing.

Prepared 2026-10-22. The owner has Meta Ray-Ban Display glasses and a Meta Neural Band and confirms remembered login works after Display build 3. Lensly build 4 changes the interface and adds a composer image menu; these new controls need on-device acceptance. Live local Ollama vision has passed; no Gemini key has been provided. The owner manually started a Cloudflare tunnel. Public HTTPS pairing and real Ollama text/image responses have passed desktop-browser verification; see glasses-session.md for the current session URL. Local tests do not pass the device gates.

## Before the device session

1. Complete the README's local setup and verify the same production web build against the local server. Use the quality report for actual automated results.
2. Choose a configured provider. For Gemini, obtain an appropriate API key through the owner's account, inspect free-tier eligibility and data terms, place it only in local server configuration, and enable Gemini deliberately. Do not paste the key into the browser, glasses or a public URL. Local Ollama can instead use an installed vision model; see the quality report for actual local inference verification. First confirm a small text and image request locally with the provider that will be used on glasses. A local-model success does not pass Gemini live-API verification.
3. Decide and authorize the HTTPS hosting or tunnel separately. The glasses require a publicly accessible HTTPS URL with a valid certificate; Windows `127.0.0.1` and HTTP-only URLs are not the device endpoint. Configure the server's allowed host, preserve the correct scheme through any trusted proxy, and keep frontend/API on the same origin. Verify unauthorized API requests fail before connecting glasses. No deployment is implied by this checklist.
4. Check glasses software v125+ and Meta AI app v272+; update the glasses, phone app and band to their available supported versions. Record exact versions and paired-phone OS. Current [Meta setup](https://wearables.developer.meta.com/docs/develop/webapps/setup/) specifies those minimums. Feature availability can also depend on account/country eligibility.
5. Enable Developer Mode in Meta AI: Settings → App Info → tap the App version five times → Enable. Current [Meta test instructions](https://wearables.developer.meta.com/docs/develop/webapps/test/) then use App Settings → Apps → Web Apps → Connect Web App, enter the authorized HTTPS URL, and Save. Names may vary by app release. Launch LensAgent from the glasses app grid. Do not claim installation succeeded based on a generated QR or dispatched install request alone.

## Pair the glasses without typing an administrator secret

1. On a trusted desktop browser, open the same authorized LensAgent origin and connect with the administrator token from the local `.env`. This is the **LensAgent server token**, not the Gemini key.
2. Open **Settings → Create glasses pairing code**. A new code invalidates any previous unredeemed code. The eight digits are valid for five minutes and one redemption.
3. On the glasses connection screen, activate the first **One-time code from Settings** field, enter all eight digits, then select **Pair this device**. The field is `type="text"`; Meta's composer does not open for password inputs. The owner must verify that this field and its surrounding disclosure are reachable by band/captouch and that leading zeroes survive.
4. Leave **Remember this device** selected and confirm the private workspace loads without entering the administrator token on glasses. Display build 3 stores the paired token and its seven-day expiry in localStorage; reopening the same installed app should restore it. Test this on the hardware. Unchecking the option keeps a session-only login. Disconnect erases both stores; removing the app, clearing storage or changing the tunnel hostname may require re-pairing sooner.
5. Pair any phone browser separately using a fresh code. These devices share one owner's workspace; do not distribute codes to other people. Pairing is not a multiuser account system.

Use [Meta's input documentation](https://wearables.developer.meta.com/docs/develop/webapps/build/input-and-navigation/) as the expected platform behavior. The code entry flow is implemented; successful handwriting entry on the owner's hardware remains a test result to collect.

## Ordered acceptance tests

Record Pass/Fail/Blocked, exact versions, steps and evidence for each row. Do not record prompts/images or tokens in public issue reports.

| Test | Procedure | Required evidence | Current result |
| --- | --- | --- | --- |
| Launch and layout | Open the authorized build; inspect Ask, Images, History and Settings in bright/dark surroundings. | Readable text, no blocked edge controls, sensible overflow at actual device viewport. | Pending |
| Navigation | Traverse each control with band/captouch; activate once; exercise native Back. | No trapped focus, duplicate actions or disappearing essential controls. | Pending |
| Pairing | Follow the pairing procedure, then try the already-used code in another browser. | Glasses gain access; reused code is rejected; administrator actions stay protected. | Pending |
| Silent text | Activate the question field, handwrite a short question, commit, then select Ask. | Correct committed text, one request, genuine configured-provider answer on glasses. | Local provider and HTTPS ready; hardware check pending |
| Conversation continuity | Ask a follow-up, change view, reopen History, then reload the app. | Correct conversation and previous turns; loss of browser token gives a clear re-pair path. | Pending |
| Image upload fallback | Open the same conversation from History on an authorized phone/desktop. Upload a nonsensitive JPEG/PNG/WebP. | Real decoded image appears in that conversation's Images view. | Pending |
| Cross-device refresh | On glasses, open History again and reopen that exact conversation after upload. | Uploaded image is visible and selectable. This is manual refresh, not live synchronization. | Pending |
| Vision and follow-up | Select that image, ask about a visible detail, then ask a second question without re-upload. | Actual selected image bytes reach provider; genuine answers refer to the right image. | Live local provider verified; device path pending |
| Replace/clear | Upload/select a different image; then Clear image and ask a text-only question. | Selected context changes; the cleared request sends no image bytes. | Pending |
| Deletion | Delete a disposable test image, then its test conversation. | Image disappears on refresh, cannot be reused, and conversation disappears. Earlier image descriptions remain until conversation deletion. | Pending |
| Failure/recovery | Test a disconnected network, unavailable provider, invalid image and expired session. | Clear failure, preserved useful UI, no automatic duplicate generation. | Pending |
| Revocation | On desktop Settings, revoke paired devices, then make a new glasses request. | Further glasses API access fails and requires pairing again. | Pending |
| Session boundaries | Test phone lock, glasses removal/replacement, app exit and later return. | Record real lifecycle behavior; do not assume background execution or permanent session storage. | Pending |

For image tests, the phone's capture/import/selection workflow is an explicit fallback. Glasses photos may arrive as HEIC on iOS; convert to JPEG/PNG/WebP before upload. The app's picker does not connect to the glasses camera or first-party Gallery. Selecting an application-stored image on glasses is different from browsing the glasses' entire photo library.

## Retention test

Default cleanup removes images older than seven days and conversations inactive for seven days when relevant API operations next run; it is not a scheduled seven-day deletion job. For a disposable test database, a developer can age fixtures and trigger a conversation/image read, then verify expired records and image references disappear. Do not alter timestamps or retention settings in valuable user data merely to run this test. Active conversations can retain older text, and provider-side deletion has separate terms. Automated fixture coverage belongs in the test report.

## Native camera track — separate future gate

No native mobile app or web/native camera bridge is implemented. A future iOS spike needs a configured Mac/Xcode and signing setup plus current official DAT samples. Pin the SDK; at this research date both SDKs report 1.0.1. Test registration, permission denial, actual camera bytes, disconnect/reconnect, lock/background behavior and display delivery. Standalone high-quality photo capture, Inputs and voice invocation include experimental capabilities whose distribution restrictions must be checked. Do not infer handwriting access from native input events.

Only after a supported handoff and shared conversation identity are demonstrated should this become the integrated no-phone camera workflow. Current references: [iOS SDK](https://github.com/facebook/meta-wearables-dat-ios), [Android SDK](https://github.com/facebook/meta-wearables-dat-android), [platform findings](../research/meta-platform.md).

## Evidence record

For each device run, retain the date, build/commit, phone OS, Meta AI app version, glasses firmware, band firmware, provider/model, sanitized steps and observed result. Use a display recording only when the owner chooses to capture it and it contains no private material. A desktop browser or [Meta simulator](https://chromewebstore.google.com/detail/jpjlmmodokemlepklkdbimceggpbjcll) result is useful preparation but must remain labeled separately from hardware verification.
