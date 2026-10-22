# Repository landscape

Reviewed 2026-10-22. Public README/source/license files, recent commit metadata, open issues and available pull requests were inspected. No candidate was built, installed or exercised on hardware. No third-party source code was copied into LensAgent in this research. Repository claims remain claims unless independently verified.

| Candidate | Observed maintenance / license | Useful evidence | Decision |
| --- | --- | --- | --- |
| [Meta DAT iOS](https://github.com/facebook/meta-wearables-dat-ios) | Release 1.0.1, Oct 9; commit `bbae597`; 42 open issues/PRs at retrieval. Custom Meta Developer Terms. | Current CameraAccess and DisplayAccess samples; explicit session lifecycle, typed failures, display widgets and mock preview. | Primary native reference. Consume official SDK under its terms; do not treat samples as MIT. |
| [Meta DAT Android](https://github.com/facebook/meta-wearables-dat-android) | Release 1.0.1, Oct 9; `f4371bc`; 25 open issues/PRs. Custom Meta Developer Terms. | 1.0.1 camera buffer/performance fixes; current `DeviceSession` → `Camera` → stream model. | Primary Android reference if owner uses Android. Native Windows host SDK is not established. |
| [Meta web-app toolkit](https://github.com/facebook/meta-wearables-webapp) | Main commit Oct 13, `038a8b0`; repository pushed Oct 18; 15 open issues/PRs. Root license is BSD-style, despite GitHub `NOASSERTION`. | Device composer guidance, app shell, simulator/test guidance and performance targets. | Adopt platform knowledge; prefer current framework-neutral docs over older fixed-size examples. |
| [Meta Display UI toolkit](https://github.com/facebook/meta-ray-ban-display-ui-toolkit-web) | Main commit Oct 20, `c374e42`; no open issues at retrieval; Apache-2.0. | Maintained components and wearable layout/focus conventions. | Optional future adoption if UI complexity justifies React/toolkit dependencies. Plain semantic HTML is supported. |
| [Chief](https://github.com/lugovelb/chief-glasses-open) | Initial main commit Oct 21, `b54219e`; no open issues; MIT. | Small display chat, quick replies, encrypted static feed and explicit Forget control. | Useful interaction reference. Not a complete Gemini camera assistant; avoid its public relay/static-public-feed architecture for this private backend. |
| [GemGlasses](https://github.com/lpecom/GemGlasses) | Single main commit Jul 13, `5663438`; no open issues; LICENSE explicitly MIT plus external SDK/API terms. | Backend/device interfaces, Gemini Live reconnect logic and mock separation. | Do not adopt the native implementation as working. Current code is incompatible with current DAT and default tests use mock glasses. |
| [OpenVision](https://github.com/rayl15/OpenVision) | Main commit Oct 4, `1d5d920`; 7 open issues/PRs; MIT. | Provider contract with image capability, bounded conversation designs, camera processing and local inference experiments. | Borrow architectural ideas; do not import its large tool/voice stack. DAT pinned to 0.9.0, iOS18+, no Display module in inspected target. |
| [VisionClaw](https://github.com/sseanliu/VisionClaw) | Main commit Oct 21, `3f39807`; 41 open issues/PRs; root license only Meta Developer Terms. | Active camera-to-agent/voice gateway experiments. | Reference only. Reuse rights for non-SDK additions are not clearly established; no copying. Scope and command permissions exceed LensAgent's MVP. |

## What source review changed

### Official SDKs are the native integration baseline

The official iOS [camera view model](https://github.com/facebook/meta-wearables-dat-ios/blob/main/samples/CameraAccess/CameraAccess/ViewModels/CameraViewModel.swift) maintains connection, permission, stream and recording states explicitly. The [DisplayAccess README](https://github.com/facebook/meta-wearables-dat-ios/blob/main/samples/DisplayAccess/README.md) covers real registration plus phone/desktop preview. These are executable sample projects, but that does not make them LensAgent integrations or guarantee reliability on the owner's firmware.

An open [iOS report #356](https://github.com/facebook/meta-wearables-dat-ios/issues/356) describes a 1.0.1 stream entering a streaming state without delivering frames on Gen 2 firmware 129. It is a user report, not a confirmed general Ray-Ban Display defect. It demonstrates why receiving actual bytes must be the acceptance criterion. [PR #161](https://github.com/facebook/meta-wearables-dat-ios/pull/161) concerns iOS target configuration. Android [issue #218](https://github.com/facebook/meta-wearables-dat-android/issues/218) reports private-beta registration/attestation failure; account/release-channel testing is separate from mock compilation.

### Web platform documentation is more authoritative than old examples

The current [web device source](https://github.com/facebook/meta-wearables-webapp/blob/main/plugins/meta-wearables-webapp/skills/ai-glasses-webapp-device/SKILL.md) documents normal text fields and committed composer input. The repository's custom shell still contains fixed 600-pixel dimensions; current [layout docs](https://wearables.developer.meta.com/docs/develop/webapps/build/display-and-layout/) explicitly recommend responsive layout and 600 × 600 validation instead.

[Issue #33](https://github.com/facebook/meta-wearables-webapp/issues/33) asks for web camera access and a DAT bridge; its only inspected reply also requests the feature. Neither establishes implementation support. [Issue #31](https://github.com/facebook/meta-wearables-webapp/issues/31) reports registered WebMCP tools not being invoked. Avoid making WebMCP or voice invocation the silent-text MVP's dependency. The repository also has dependency-update PRs, including [#32](https://github.com/facebook/meta-wearables-webapp/pull/32); this is evidence of maintenance activity, not a security audit of all templates.

### GemGlasses illustrates a dangerous mock-to-hardware gap

[RealGlassesBackend.kt](https://github.com/lpecom/GemGlasses/blob/main/app/src/realGlasses/java/com/lpecom/gemglasses/glasses/real/RealGlassesBackend.kt) imports `StreamSession` and calls `Wearables.openCameraStream()`. Its [version catalog](https://github.com/lpecom/GemGlasses/blob/main/gradle/libs.versions.toml) selects DAT 0.5.0. The current official 1.0.1 flow uses explicit sessions/camera capabilities; those source calls must not be considered current supported API examples. The README says mock glasses are the default build. Therefore the claimed unit-test/build success does not verify real camera access. Its separate provider and device interfaces are still a useful design pattern. The app-secret/token service would also need authentication, abuse controls and threat review before external exposure.

### OpenVision is useful but substantially broader than this MVP

[AIBackendProtocol.swift](https://github.com/rayl15/OpenVision/blob/main/OpenVision/Services/AIBackend/AIBackendProtocol.swift) makes image support an explicit capability. [GeminiVisionService.swift](https://github.com/rayl15/OpenVision/blob/main/OpenVision/Services/GeminiLive/GeminiVisionService.swift) separates frame cadence, connection state and query handling. [project.yml](https://github.com/rayl15/OpenVision/blob/main/project.yml) pins DAT 0.9.0 and includes Core/Camera, not Display. It also contains local MLX and extensive tool execution; neither is needed for a first private text/image API.

Recent [PR #73](https://github.com/rayl15/OpenVision/pull/73) tightens handling of plaintext HTTP host guesses. The open [#74](https://github.com/rayl15/OpenVision/issues/74) reports an XProtect build warning; no conclusion about maliciousness was established. Treat remote agent tools, subscription-login integrations, model downloads and plaintext endpoints as separate reviews rather than inheriting them wholesale.

### Chief helps with interaction, not the complete transport

[Chief's README](https://github.com/lugovelb/chief-glasses-open/blob/main/README.md) describes a public encrypted JSON feed and optional email/ntfy relays. [publish.py](https://github.com/lugovelb/chief-glasses-open/blob/main/publish.py) uses AES-GCM and password-derived keys; this is real encryption code, not an AI backend. The browser stores its passphrase, and publishing the feed involves external hosting. Its latest commit includes fixes for message ordering, deletion safeguards and quick-reply focus. These support simple quick replies and explicit deletion UX, but do not prove camera integration or safe private messaging for LensAgent.

## Reuse policy and architectural outcome

Use original LensAgent code around a small provider contract, authenticated API and SQLite storage. Use the official Google SDK for Gemini, current Meta APIs only for a future native component, and standard HTML for the supported web composer. Preserve a distinction between mock/provider tests and actual device tests.

No candidate warrants replacing the backend with a larger framework. Avoid copying obsolete model identifiers, old native API names, bundled secrets, permissive remote-command paths or community assertions of hardware support. Any future code reuse must retain the applicable license/attribution and identify the exact commit. GitHub's automatic license classification is insufficient; inspect the license file, as GemGlasses and Meta's web repository demonstrate.

Messaging bot research is recorded separately in `messaging-feasibility.md`; model SDK/Ollama findings are in `ai-models.md`. OpenAI/Codex agent execution remains future work and must not be exposed through this application's chat endpoint without a separate permission design.
