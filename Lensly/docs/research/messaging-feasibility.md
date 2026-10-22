# Messaging feasibility

Research date: 2026-10-22. No Meta messaging account, application permissions, live webhook, or glasses session was used in this research. **All messaging-to-glasses workflows are Not Yet Hardware-Verified.**

## Decision

Do not make a Messenger Page bot or Instagram professional-account bot the primary LensAgent interface yet. The APIs support business conversations; the missing proof is that those specific business/bot conversations can be selected, composed, and read in the glasses UI. Normal-contact support is insufficient evidence.

Prefer the documented Display web-app text-entry path, with a local browser interface for development. Keep messaging as a conditional adapter after the hardware gates below pass. This is an engineering choice, not a claim that Page bots are impossible.

## Glasses evidence

| Capability | Evidence and status | Consequence |
|---|---|---|
| Messenger, Instagram, WhatsApp and phone messaging | Ray-Ban's official [Display FAQ](https://www.ray-ban.com/usa/c/frequently-asked-questions-meta-ray-ban-display) describes connected providers and selecting contacts. High confidence as documented product behavior. | A paired phone and Meta AI app are part of this workflow. It does not establish bot-account eligibility. |
| Silent handwriting | Meta's [2026-03-31 announcement](https://about.fb.com/news/2026/03/meta-ai-glasses-built-for-prescriptions/) describes expanded Neural Handwriting across these messaging channels. High confidence in announced functionality; installed firmware/account behavior remains untested. | Do not repeat the obsolete January-only Messenger/WhatsApp restriction as current fact. |
| Existing-photo sharing | The Display FAQ describes import to the phone photo library, then Gallery selection and contact sharing from glasses. It lists JPEG on Android and HEIC on iOS. | Gallery is not a documented arbitrary upload API. HEIC compatibility or conversion must be tested before an image adapter is complete. |
| Page bot / professional bot visibility | Neither inspected official source explicitly confirms these account types in glasses contacts, recent conversations or share destinations. | Unknown; requires a real device test. |
| Web-app handwriting | Current [Meta wearables FAQ](https://developers.meta.com/wearables/faq/) explicitly documents HTML/CSS/JS apps on Display and handwriting, dictation and keyboard text input. | Stronger documented basis for text entry than a bot-contact assumption. Full application transport and hardware behavior still need testing. |

## Messenger Platform

The [official Meta Postman Send API collection](https://www.postman.com/meta/messenger-platform-api/folder/vilwbh4/send-api) documents a Page access token issued for a person with the Page's messaging task and `pages_messaging`. Ordinary automated replies use the standard 24-hour window following the user's message; any outside-window mechanism requires its own eligibility. LensAgent must not assume a human-agent exception authorizes automated AI replies.

The [official text request](https://www.postman.com/meta/messenger-platform-api/request/poazquh/text-message) uses `POST https://graph.facebook.com/{version}/{page-id}/messages`, a Page-scoped recipient ID, and a text message. The [media reference](https://www.postman.com/meta/messenger-platform-api/documentation/iyp204x/messenger-platform-api?entity=folder-22794852-9fcfb7b7-1d80-422d-b5c8-eb2b1003d4fc) supports image attachments. Receiving a message and downloading its image bytes are separate operations; a URL in an event is not evidence that Gemini received an image.

The [Conversations API reference](https://www.postman.com/meta/messenger-platform-api/folder/22794852-255610cd-47f5-4f4d-b3fa-71aec360be9a) lists `pages_manage_metadata`, `pages_read_engagement` and `pages_messaging` for its Messenger conversation queries. It requires Advanced Access for conversations outside app/business roles. Request only permissions actually required by the chosen endpoints. Public availability must await the applicable App Review and account checks; developer-role testing does not prove public eligibility.

The collection's example still displays `v20.0`; it is an example, **not a verified latest Graph version**. Before an adapter is enabled, select a currently supported version in the account dashboard and pin it in server configuration. No exact current per-Page throughput or media-byte ceiling was independently verified in this session. Handle rate-limit responses and `Retry-After`, keep outgoing answers short, and check the current endpoint limits during account setup.

## Instagram messaging

The [official Instagram API with Instagram Login reference](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api?entity=request-23987686-fc851f39-7194-4522-a475-2cea8de46d16) requires an Instagram professional account, an appropriate token and `instagram_business_manage_messages`; basic account access uses `instagram_business_basic`. The recipient must initiate the conversation. Group messaging is unsupported; shared media may arrive as a URL. Testers need the documented roles and permissions. General-purpose personal-account automation is not this API.

Do not mix Instagram Login scopes with the older Facebook Login path: the latter has different Page linkage, token and permission requirements. The [official text endpoint example](https://www.postman.com/meta/instagram/request/scob1z4/text-message) uses `graph.instagram.com/{api_version}/me/messages`, an Instagram-scoped recipient ID and message text. Treat automated replies as confined to the standard service window until the current policy and dashboard confirm otherwise; no expanded automated window was verified. Professional-account visibility in Display's IG Direct experience remains unknown.

## WhatsApp

Do not select WhatsApp Cloud API for the initial general-purpose LensAgent assistant. The search-indexed [official Business Solution Terms](https://www.whatsapp.com/legal/business-solution-terms?lang=pa&locale=ca_ES), marked modified 2026-03-06, restrict AI providers where AI is the primary service, with exceptions for EEA- and Brazil-country-code users. This is not a universal permission to operate an AI bot.

On direct inspection the terms redirected to a login-protected [Meta Terms for WhatsApp Business Platform page](https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform). Therefore the account's currently applicable October terms, any geographic exception, and current AI-provider pricing were **not fully verified**. The implementation must stay disabled pending that review. No free-operation assumption is warranted, and no WABA, number, billing or external account was created.

## Security requirements for any later messaging adapter

Meta's [official Python webhook sample](https://github.com/fbsamples/messenger-platform-samples/blob/main/messenger-api/messenger-api-and-webhooks/app.py) verifies the GET subscription challenge and checks `X-Hub-Signature-256` against an HMAC-SHA256 of the raw body using the App Secret. Its older [JavaScript helper](https://github.com/fbsamples/messenger-platform-samples/blob/main/utils/webhook-signature.js) still uses SHA-1. This inconsistency is a reason to implement and test the current SHA-256 contract explicitly, not copy an entire sample.

The LensAgent adapter's engineering acceptance criteria are:

- Require nonempty secrets; compare tokens/signatures in constant time; reject missing, malformed or wrong-algorithm signatures before parsing content. The verification token, App Secret and Page access token are different secrets.
- Validate expected Page/account ID, allowlisted sender ID and event type. Ignore echo, delivery and read events without invoking the model.
- Persist event IDs and outgoing delivery state. Deduplicate before inference; a valid HMAC alone does not prevent replay. Recover interrupted deliveries without silently generating a second paid response.
- Acknowledge only after durable acceptance. Process bounded work off the webhook path; apply capped retries and explicit failed-delivery state.
- Fetch only permitted HTTPS media origins, check every redirect and resolved address, block private/link-local targets, cap streamed bytes and decoded pixels, verify MIME/content, strip metadata, and avoid logging private URLs or message bodies. Prefer rejecting remote URLs over a weak SSRF filter.
- Enforce conversation ownership, retention/deletion, response-window rules and local daily budgets. Do not connect incoming messages to shell execution or repository mutation.

These are future adapter requirements, not a claim that a messaging implementation exists.

## Hardware go/no-go test

With the owner's existing, authorized accounts and a test Page/professional account:

1. Start the bot conversation on the phone, then locate that exact conversation on Display. Record firmware, Meta AI app version, provider and account type.
2. Compose a handwritten question on the glasses. Confirm the same text arrives in a signed webhook with the expected scoped IDs.
3. Send a short backend-generated reply and confirm it appears inside that glasses conversation.
4. Capture a photo, then share it to the same account from the glasses. Verify actual decoded bytes reach the backend; repeat with an older Gallery photo and with iOS HEIC if relevant.
5. Ask a follow-up without resending the image. Verify the same conversation and retained image are used.
6. Repeat after app restart, phone lock and an expired reply window. Confirm failures are visible and no out-of-window automated messages are sent.

**Pass requires all six steps for the selected channel.** A phone-only API success cannot pass the glasses gate. If contact discovery fails, return to the web-app route instead of unsupported personal-account automation.

## Research limitations

Several `developers.facebook.com` documentation endpoints returned HTTP 429 through the research browser. The official Meta-owned Postman workspaces and official sample repository supplied readable API evidence. No authenticated Meta dashboard was inspected. Rate limits, current Graph version, complete media-format matrices, account review eligibility, and WhatsApp's redirected terms remain setup checks rather than fabricated values.
