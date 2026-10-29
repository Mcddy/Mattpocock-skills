---
name: "web-to-store"
description: "Turn a web app, site or other software into an iOS and Android app that can pass App Store and Google Play review. Use for 'make this an app', 'get this on the App Store or Play Store', wrapping with Capacitor, mobile UX refits, mobile performance or security hardening, store listings, and submission checklists."
---

# Web to Store

Take existing software and ship it as a real iOS and Android app. The job is not "wrap it in a WebView". Wrapped websites are the classic rejection. The job is a pipeline: audit, choose a route, build the native shell, refit the UI for a phone, add native value, tune performance, harden security, prepare compliance and store assets, build and sign, submit.

## Operating rules

1. Read the code before asking anything. Detect what you can; ask only what the repo cannot tell you (accounts, hardware, whether digital goods are sold).
2. Work on a branch. Never rewrite the web app in place.
3. Store rules change every year. Section 9 lists the facts that expire, with the date they were checked. Before relying on any of them, re-check the linked primary source and say if it changed.
4. Never say "store ready" unless every item in the Readiness Gate (section 8) passes. Report failures as failures.
5. Never ask for, print, or commit signing keys, keystore passwords, API keys or Apple/Google credentials. Tell the user where to put them (CI secrets) and reference them by name.
6. Review outcomes are decided by humans at Apple and Google. State residual risk plainly; do not promise approval.
7. Some steps only the account holder can do: enrol in developer programmes, verify identity, accept agreements, pay fees, press Submit. List these explicitly as HUMAN steps.

## 1. Intake: what to detect

Produce a short table before planning.

| Question | How to find out |
|---|---|
| Framework and build output | package.json, build config, is there a static `dist`/`build`? |
| Rendering model | SPA, static, or server-rendered (Next/Nuxt SSR, Rails, Django, PHP)? |
| Routing | history vs hash; deep-linkable paths |
| Auth | cookie sessions, JWT in localStorage, OAuth providers, social logins |
| Money | Stripe or other checkout; are the goods digital or physical/services? |
| Data | APIs called, offline needs, local storage use |
| Device features already used | camera, geolocation, file upload, notifications |
| Secrets in the bundle | grep for keys, tokens, `.env` values compiled into client code |
| Web-only patterns | hover menus, tooltips, right-click, wide tables, fixed desktop widths, modals, cookie banners |
| Third-party SDKs | analytics, ads, crash reporting (each affects privacy declarations) |
| Dev machine | Windows, macOS or Linux. No Mac means iOS builds must run in cloud CI. |
| Accounts | Apple Developer Program and Google Play Console: enrolled, individual or organisation? |

## 2. Route: pick one and say why

| Source | Route | Notes |
|---|---|---|
| SPA or static build (React, Vue, Svelte, Angular, plain HTML/JS) | **Capacitor**, web assets bundled inside the app | Default. One codebase, real native shell, plugin access. |
| Server-rendered app with no static build | Extract a client: static export or SPA shell talking to the existing backend as an API, then Capacitor | Pointing a WebView at the live URL is the highest-risk route for Apple guideline 4.2. Use it only as a stopgap and say so. |
| Good PWA, Android only | Trusted Web Activity (Bubblewrap or PWABuilder) | Fast for Play. Does not solve iOS. |
| React app that needs heavy native UI, long lists, complex gestures or 60 fps animation everywhere | React Native / Expo: reuse logic, rebuild the view layer | Bigger job. Choose it only when WebView performance is the proven blocker. |
| Electron app | Reuse the renderer in Capacitor; replace Node/IPC calls with plugins or backend calls | |
| Tauri app | Tauri 2 mobile targets | Check plugin coverage first. |
| Backend, CLI, script, desktop-native software with no web UI | Design a mobile client first (screens, API), then apply this skill | Say this is a new front end, not a conversion. |
| Canvas or WebGL game | Capacitor | Measure frame rate on a low-end Android early. |

If two routes fit, choose the one with less rewrite and name the trade-off in one line.

## 3. Native shell (Capacitor default)

- Add Capacitor to the existing project; set `webDir` to the build output; add `ios` and `android` platforms.
- App ID in reverse-domain form. It is permanent on both stores: confirm it with the user before first upload.
- Bundle web assets locally. Do not set `server.url` in release builds.
- `capacitor.config`: restrict `server.allowNavigation` to the hosts the app truly needs; keep `androidScheme` as `https`; `cleartext: false`.
- Open external links in the system browser (Browser plugin), never inside the app WebView.
- Handle the Android back button and predictive back with the App plugin: go back in history, close open sheets first, exit only from the root.
- Status bar, splash screen and keyboard plugins configured, not left at defaults.
- Fix web assumptions that break under a `capacitor://` or `https://localhost` origin: absolute URLs, cookies with SameSite, CORS on the API, service workers, OAuth redirect URIs.

Done when: the app launches from a release build on a real Android device and an iOS build (device or TestFlight) with no network errors and no blank screens.

## 4. Mobile refit: make it feel like an app

Design at 360 x 640 dp (small Android) and 390 x 844 pt (iPhone). Then check 320 pt wide and the largest phones.

**Layout**
- One primary action per screen. Put it in the bottom third, where a thumb reaches.
- Navigation: bottom tab bar with 3 to 5 destinations for top-level sections; stack navigation with a back affordance inside each. No hamburger menu as the only navigation.
- Single column. Convert wide tables to cards or lists with the two or three fields that matter, detail on tap.
- Convert modals to full-screen pages or bottom sheets. Convert multi-column forms to one column, one question group per screen if long.
- Remove web furniture: site header and footer, cookie banner, breadcrumb trails, "open in browser" dead ends, visible URLs, desktop sidebars.

**Touch**
- Minimum target 44 x 44 pt on iOS and 48 x 48 dp on Android, with at least 8 dp between targets.
- Replace every hover, tooltip and right-click with a tap, long-press menu or visible control.
- Give pressed states to everything tappable. Add light haptics to confirmations and destructive actions, not to every tap.

**Gestures**
- iOS edge swipe back and Android back must both work on every pushed screen.
- Pull to refresh on lists that can go stale.
- Swipe actions on list rows (archive, delete) only with an undo and with the same action reachable by tap.
- Bottom sheets drag to dismiss. Carousels use scroll snapping.
- Keep custom horizontal swipes away from the screen edges so they do not fight system gestures.
- Every gesture needs a visible, tappable alternative. Gestures are shortcuts, never the only path.

**Safe areas and viewport**
```css
:root { --sat: env(safe-area-inset-top); --sab: env(safe-area-inset-bottom); }
html, body { height: 100%; overscroll-behavior-y: none; -webkit-tap-highlight-color: transparent; }
.app { min-height: 100dvh; padding-top: var(--sat); padding-bottom: var(--sab); }
.tabbar { padding-bottom: max(8px, var(--sab)); }
input, select, textarea { font-size: 16px; } /* below 16px iOS zooms the page on focus */
button, a, [role=button] { touch-action: manipulation; }
```
Viewport meta needs `viewport-fit=cover`. Android now draws edge to edge: content must not sit under the status or gesture bars.

**Keyboard and forms**
- Correct `inputmode`, `autocomplete`, `enterkeyhint` on every field so the right keyboard and autofill appear.
- The focused field and the submit button stay visible above the keyboard.
- Support password managers and one-time-code autofill.

**States and system behaviour**
- Design loading (skeletons), empty, error and offline states for every data screen. A white screen with a spinner is a rejection risk and a bad app.
- Detect offline and say so; queue or disable actions rather than failing silently.
- Dark mode follows the system unless the brand forbids it.
- Text scales with the system font size to 200 percent without clipping. Respect reduced motion.
- Decide orientation deliberately: lock to portrait unless landscape is designed.
- Restore scroll position and form input when the app returns from the background.

Done when: a person can complete the three most important tasks one-handed on a small phone without pinching, zooming or mis-tapping.

## 5. Native value (this is what clears Apple 4.2)

Apple's guideline 4.2 says an app should "include features, content, and UI that elevate it beyond a repackaged website". Add the native capabilities that fit the product. Pick the ones that help the user; do not bolt on gimmicks.

- Push notifications tied to real events, with the permission prompt shown in context after a pre-prompt, never on first launch.
- Biometric unlock for returning sessions.
- Native share sheet, and being a share target if the app receives content.
- Camera, photo picker, file picker, scanner, in place of web file inputs.
- Deep links: Universal Links on iOS and verified App Links on Android, so shared URLs open the app at the right screen.
- Offline access to the user's own recent data.
- Home screen quick actions, widgets, or system search indexing where they fit.

Record in the review notes which native features the app has. Reviewers look for them.

## 6. Performance

These are engineering targets, not store rules. Measure on a mid-range or low-end Android phone; that is where WebView apps fail.

| Target | Value |
|---|---|
| Cold start to usable first screen | under 2 s on a mid-range Android |
| Tap to visual response | under 100 ms |
| Scrolling and transitions | 60 fps, no dropped frames on list scroll |
| Initial JavaScript | as small as route-splitting allows; flag anything over about 300 KB gzipped |

Tactics, in order of usual payoff:
1. Ship assets inside the app; never load the UI from the network.
2. Split code by route; lazy-load anything not on the first screen.
3. Virtualise lists longer than about 50 rows.
4. Animate only `transform` and `opacity`. Remove `backdrop-filter`, large blurs and heavy shadows on scrolling content; they are expensive in Android WebView.
5. Images: correct size, WebP or AVIF, lazy below the fold, fixed dimensions to stop layout shift.
6. Cache API responses and show stale data immediately, then refresh.
7. Subset fonts; prefer system fonts for body text.
8. Passive scroll and touch listeners; no layout reads inside scroll handlers.
9. Keep the splash screen until the first screen is painted, then hide it. No white flash.
10. Watch memory: release large images and listeners on navigation.

Profile with Chrome remote debugging (`chrome://inspect`) on Android. Safari Web Inspector for iOS needs a Mac; without one, rely on Android profiling plus TestFlight testing on a real iPhone.

## 7. Security hardening

Structured on the OWASP MASVS control groups. First principle: everything inside the app bundle is public. Anyone can unzip it.

**Storage (MASVS-STORAGE)**
- Session and refresh tokens go in the iOS Keychain and Android Keystore through a secure-storage plugin. Never in localStorage, never in plain preferences.
- No personal data, tokens or request bodies in logs.
- Android: set `android:allowBackup="false"` or define backup rules that exclude sensitive files.
- Screens showing sensitive data: block screenshots on Android (FLAG_SECURE) and cover the app-switcher snapshot on iOS.

**Crypto (MASVS-CRYPTO)**
- Platform crypto only. No hand-rolled algorithms, no hard-coded keys or IVs.

**Auth (MASVS-AUTH)**
- OAuth and social login run in the system browser sheet (ASWebAuthenticationSession, Custom Tabs) with PKCE. Never collect third-party passwords in an embedded WebView.
- Short-lived access tokens, rotating refresh tokens, server-side revocation on logout and on account deletion.
- Biometric unlock must release a Keystore or Keychain-bound secret. A boolean "unlocked = true" is not security.
- Authorisation is enforced on the server for every request. The client is never trusted.

**Network (MASVS-NETWORK)**
- HTTPS only. iOS App Transport Security stays on with no arbitrary-loads exception. Android `usesCleartextTraffic="false"` plus a network security config.
- Certificate pinning only if the team can run key rotation without bricking installed apps. For most apps, correct TLS plus server-side controls is the better trade. State the choice.

**Platform (MASVS-PLATFORM)**
- WebView lockdown: navigation allow-list, a Content Security Policy, no remote scripts, no JavaScript bridge exposed to content the app did not ship.
- Validate every deep link parameter as untrusted input. Deep links must not perform state-changing actions without confirmation.
- Android components `exported="false"` unless they must be public.
- Request the minimum permissions, at the moment of use, with honest purpose strings.

**Code (MASVS-CODE)**
- Move any secret found in client code to a backend proxy. Rotate it; it has already leaked.
- Release builds: WebView debugging off, no source maps shipped, console logging stripped, R8 minification on for Android.
- `npm audit` and plugin versions current; target SDK current.
- Validate and encode all data rendered into the WebView (XSS becomes native-bridge access in a hybrid app).

**Resilience (MASVS-RESILIENCE)**
- Only where the threat model needs it (payments, anti-fraud, paid content): Play Integrity and App Attest, verified on the server. Root and jailbreak checks are a speed bump, not a control. Say so.

**Privacy (MASVS-PRIVACY)**
- Collect the minimum. Inventory every SDK and what it sends.
- iOS privacy manifest, including approved reasons for required-reason APIs used by the app or its SDKs.
- Store privacy declarations must match actual behaviour (see section 8).

**Live updates**
- Apple guideline 2.5.2 forbids downloading code that "introduces or changes features or functionality". Over-the-air web-asset updates are a risk area: use them for fixes, not for shipping new features past review, and flag the risk to the user.

Output a findings table: issue, MASVS group, severity, file, fix, status.

## 8. Compliance, store assets and the Readiness Gate

**Common rejection causes to design out**

| Rule | What it requires |
|---|---|
| Apple 4.2 minimum functionality | More than a repackaged website. Sections 4 and 5. |
| Apple 2.1 completeness | No crashes, placeholders or dead links; a working demo account in the review notes with the backend switched on. |
| Apple 5.1.1(i) | Privacy policy linked in App Store Connect and inside the app. |
| Apple 5.1.1(v) | No forced login for features that do not need an account. If accounts can be created, account deletion must be offered inside the app. |
| Apple 4.8 | If a third-party or social login is the primary account, also offer a privacy-preserving login option (Sign in with Apple satisfies this). |
| Apple 3.1.1 | Unlocking digital features, content or subscriptions inside the app uses in-app purchase. Physical goods and real-world services use other payment methods. External purchase link rules differ by storefront and have changed repeatedly: verify the current text before advising. |
| Apple 2.3 | Screenshots show the app in use, not a splash or login screen; metadata is accurate. |
| Google Data safety | Form answers match what the app and its SDKs actually collect and share. |
| Google target API | Meets the current target API level. |
| Google testing rule | New personal accounts must complete a closed test before production access. |
| Both | Every permission has a clear, specific purpose string and is actually used. |

**Store assets to produce in a `store/` folder**
- `listing.md`: app name, subtitle or short description, full description, keywords, promotional text, category, support URL, marketing URL. Respect each store's character limits and check them.
- `screenshots.md`: a shot list of 5 to 8 screens in story order with caption text, and the pixel sizes currently required.
- `icon` guidance: 1024 x 1024 with no transparency for Apple; adaptive icon layers and a 512 x 512 listing icon for Google; a 1024 x 500 feature graphic for Google.
- `privacy.md`: data inventory, answers for Apple's privacy details and Google's Data safety form, privacy policy checklist.
- `review-notes.md`: demo account, how to reach every feature, list of native capabilities, explanation of anything unusual.
- `age-rating.md` and export-compliance answer (standard HTTPS-only encryption normally qualifies for the exemption; confirm for the app).
- `SUBMISSION_CHECKLIST.md`: ordered steps, each marked AGENT or HUMAN.

**Readiness Gate** (all must pass)
- [ ] Release builds install and run on a real Android phone and a real iPhone
- [ ] No crash, blank screen or placeholder on any reachable screen; offline handled
- [ ] Small-screen pass: targets, safe areas, keyboard, back navigation, text scaling
- [ ] At least two native capabilities that serve the product
- [ ] No secrets in the bundle; tokens in secure storage; cleartext off; WebView locked down
- [ ] Privacy policy live; in-app link; account deletion in-app if accounts exist
- [ ] Login rule (4.8) and payment rule (3.1.1) satisfied or not applicable, with reasoning
- [ ] Privacy manifest and both stores' privacy declarations match real behaviour
- [ ] Target API, SDK and Xcode versions meet the current requirements (re-verified today)
- [ ] Listing, screenshots, icon, review notes and demo account complete
- [ ] Signed AAB and signed IPA produced by a repeatable pipeline
- [ ] Google closed-test requirement met or scheduled, if it applies

## 9. Build, sign, test, submit

**Android** (works on Windows, macOS, Linux)
- Generate an upload keystore once; back it up outside the repo; enrol in Play App Signing.
- Build a signed Android App Bundle (AAB). Internal testing track first, then closed testing, then production.

**iOS**
- Building and signing needs macOS and Xcode. On Windows or Linux use cloud macOS CI. Options: Xcode Cloud, GitHub Actions macOS runners, Codemagic, Bitrise, or a Capacitor-specific build service. Compare current pricing before recommending one.
- Use an App Store Connect API key stored as a CI secret to manage signing and upload. No Apple ID password in CI.
- Without a Mac there is no local Simulator. Test through TestFlight on a real iPhone.
- TestFlight internal testers first, then external testers, then submit for review.

**After submission**
- If rejected: quote the cited guideline, map it to a section above, fix, and reply in the Resolution Centre with what changed. Do not argue before fixing.

## 10. Facts that expire (checked 8 October 2026)

Re-verify each before relying on it.

| Fact | Value when checked | Source |
|---|---|---|
| Apple build requirement | Since 28 April 2026 uploads must be built with Xcode 26 or later using the iOS 26 SDK | developer.apple.com/news/upcoming-requirements |
| Apple minimum deployment | Since 9 September 2026 uploads must target iOS 13 or later | same page |
| Apple Developer Program | 99 USD per year; local price shown at enrolment | developer.apple.com/programs/enroll |
| Apple seller name | Individual or sole proprietor: legal name is shown as seller. Organisation: must be a legal entity with a D-U-N-S number; trade names are not accepted | same page |
| Apple screenshots | One required iPhone size (1179 x 2556 or 1206 x 2622); iPad 13 inch required only if the app supports iPad; up to 10 per size | developer.apple.com/help/app-store-connect/reference/screenshot-specifications |
| Google target API | New apps and updates must target Android 16 (API 36) from 31 August 2026; extension to 1 November 2026 on request | support.google.com/googleplay/android-developer/answer/11926878 |
| Google testing rule | Personal accounts created after 13 November 2023: closed test with at least 12 testers opted in for 14 continuous days, then apply for production access | support.google.com/googleplay/android-developer/answer/14151465 |
| Google 16 KB pages | Apps targeting API 35+ with native libraries must support 16 KB page sizes; from 1 February 2027 non-compliant updates cannot be released | developer.android.com/guide/practices/page-sizes |
| Android developer verification | Enforcement begins 30 September 2026 in Brazil, Indonesia, Singapore and Thailand; global from 2027. Play developers verify in Play Console | android-developers.googleblog.com (March 2026) |
| Capacitor | Version 8: Node 22+, Xcode 26.0+, Android Studio 2025.2.1+, Android API 24+, Swift Package Manager by default | capacitorjs.com/docs/getting-started/environment-setup |
| Ionic Appflow | Reported to end service 31 December 2027 (vendor blog, not Ionic's own notice: confirm) | capgo.app blog |
| Google Play registration fee | Commonly cited as a one-time 25 USD. Not re-verified on the check date | Play Console signup |

## Output format

Deliver in this order, and stop for the user's go-ahead only where marked.

1. `MOBILE_AUDIT.md`: intake table, chosen route with reason, findings by area (UX, performance, security, compliance) with severity, and the list of HUMAN steps with fees and lead times.
2. `SHIP_PLAN.md`: phases, each with tasks and a "done when" test. **Pause here** only if the route requires a rewrite or the user lacks a required account.
3. Code changes on a branch, one phase per commit.
4. The `store/` folder.
5. The Readiness Gate, filled in honestly, with what is still open.