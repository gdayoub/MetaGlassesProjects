# Architecture decision

Decision date: 2026-10-22. Implement a local web client and provider-independent Python backend. Target the documented Ray-Ban Display web composer for silent text, while providing phone/desktop uploads and application-owned image history.

## Candidate comparison

The qualitative confidence below concerns suitability for this project. It is not a measured probability or proof of hardware operation.

| Criterion | A: Messenger Page bot | B: Instagram professional bot | C: Display web app — selected | D: Native mobile companion | E: Web/native hybrid |
| --- | --- | --- | --- | --- | --- |
| Silent handwriting | First-party messaging supports it; Page-bot selection unknown | First-party messaging supports it; professional-bot selection unknown | Documented system composer on standard text fields | No documented native handwriting composer in inspected DAT display interface | Web composer documented; transfer between experiences unproven |
| New glasses camera image | Sharing to this bot must be verified | Sharing to this bot must be verified | No camera capture API; phone/desktop upload fallback | Official camera streaming/photo APIs; permissions and hardware tests required | Native capture possible; session/handoff design required |
| Existing images | Gallery-to-bot path unverified | Gallery-to-bot path unverified | Own uploaded-image history; no arbitrary glasses Gallery access | Phone/app storage possible; no assumed glasses Gallery enumeration | Own storage possible; synchronization required |
| AI response delivery | Send API exists; display visibility unverified | Send API exists; display visibility unverified | Render API response in the web app | DAT display API exists | Web or native display possible |
| Conversation continuity | Backend keyed to validated scoped sender | Backend keyed to validated scoped sender | SQLite, explicit conversation ID and retained image selection | Must build phone/backend identity and state | Shared backend possible; cross-client coordination adds complexity |
| Free development | Local server possible; review/account prerequisites | Local server possible; professional-account/review prerequisites | Local Windows development; external HTTPS still needed for glasses | SDK tooling available; iOS requires suitable Mac/signing setup | Inherits web and native prerequisites |
| Implementation complexity | Moderate API work, critical contact uncertainty | Moderate API work, critical contact uncertainty | Lowest validated platform surface for silent text | Higher: build/signing/device lifecycle | Highest: two runtimes plus cross-app identity |
| Required hardware | Glasses, band and paired phone for acceptance | Glasses, band and paired phone for acceptance | Browser for local checks; glasses/band/phone for composer acceptance | Glasses and supported phone; Mac/Xcode for iOS | Same as native plus web access |
| Platform restrictions | Page permissions, service window, review | Professional account, initiation rules, review | HTTPS, account/country eligibility, no camera | Experimental capability restrictions and mobile lifecycle | All relevant restrictions; no seamless bridge established |
| Maintainability | API version/policy tracking; transport isolated | API version/policy tracking; transport isolated | Small semantic client, stable HTTP boundary | SDK/OS updates and device matrix | More integration surfaces and failure modes |
| Confidence in initial outcome | Conditional until bot-contact gate passes | Conditional until bot-contact gate passes | Strongest documented silent-text path; hardware test still pending | Strong camera path, weak silent-input fit today | Insufficient evidence for an integrated hands-free flow |
| Disposition | Defer adapter | Defer adapter | Build now | Future bounded camera spike | Defer until native/web interaction is demonstrated |

Evidence: [Meta platform report](../research/meta-platform.md), [messaging report](../research/messaging-feasibility.md), [repository review](../research/github-landscape.md). WhatsApp is excluded from the initial general-purpose assistant pending applicable platform-policy review.

## Selected implementation

One FastAPI process serves the compiled TypeScript client and authenticated API. The client uses semantic HTML with visible focus and responsive CSS, validated at a 600 × 600 target. Chromium's spatial navigation and system composer remain responsible for wearable input. No proprietary web-input SDK, page-wide directional focus manager, or invented camera bridge is required.

Gemini is implemented through Google's official SDK, with a separate local Ollama provider. Providers are disabled until deliberately configured. SQLite stores conversation text, normalized image bytes, request outcomes, local usage counters and pairing state. Images are uploaded as bytes; the server does not fetch arbitrary user-provided image URLs.

The deployment is a **single-owner shared workspace**. An administrator token connects a trusted desktop browser. The administrator can issue an eight-digit, five-minute, one-use pairing code so the glasses can use a supported text field instead of trying to enter the administrator token into a password composer. Paired tokens can access the same conversations and images, expire after seven days, and can be revoked. They cannot issue pairing codes or administer devices. This is not tenant isolation or a public multiuser service.

Phone/desktop and glasses clients share backend data but do not receive live push updates. After uploading from another client, refresh History and reopen the same conversation on glasses to retrieve current messages and image context. Pairing does not automatically select a matching conversation.

## Tradeoffs and boundaries

This path gives the owner editable Windows software and the best-supported silent text entry without tying the project to an unverified business-bot contact. It does not meet the complete camera-to-answer workflow from glasses alone. Direct glasses capture, first-party Gallery import, native phone background capture and seamless switching between native and web apps remain unimplemented.

No native iOS project is generated because no Mac/Xcode build/signing environment is configured. Native work should begin with current official DAT 1.0.1 samples and actual-device acceptance tests, then feed the same authenticated backend. Do not present uncompiled Swift stubs as an integration.

Local inference has no provider service charge and uses an installed model; see the quality report for actual local inference verification. Gemini's free-tier eligibility, limits and data terms require an account check; local request limits do not guarantee a zero provider bill. No billing was enabled. No public deployment or tunnel is authorized by this architecture decision.

## Revisit triggers

- If the on-device web composer or account eligibility blocks the owner, test the first-party messaging bot-contact gate before implementing a transport.
- If a Mac and authorized phone become available, build a small native camera/display spike; require real received image bytes and lock/background/disconnect tests.
- If Meta documents a web camera or supported native/web handoff, verify the exact runtime/version before changing the image workflow.
- Before public or multiuser distribution, replace shared-owner authentication with a reviewed identity and per-user authorization model, complete hosting review, and satisfy the applicable Meta distribution requirements.

Current device acceptance steps are in [the deployment guide](../setup/deployment.md). Test evidence belongs in the quality report; architectural feasibility is not a passed test.
