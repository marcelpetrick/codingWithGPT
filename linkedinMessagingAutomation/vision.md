# Vision: LinkedIn reply desk

Status: draft 0.2, 2026-10-27. Owner: Marcel Petrick. The plan, the status and "Resume here" are in
`plan.md`. The working rules are in `AGENTS.md`.

## Verdict so far

1. The tool reads, the owner sends. No code ever sends a message, accepts an invitation or clicks on linkedin.com.
2. Two read routes are worth building, both without extra traffic to LinkedIn:
   - **Route I, passive page capture (owner's idea):** you browse LinkedIn in your own Chrome. The tool
     reads the page that is already open over the Chrome DevTools Protocol (CDP), when you press "Capture".
     This adds zero requests to LinkedIn. It is a grey zone under §8.2, so it stays read-only and rare.
   - **Route A, DMA Member Data Portability API:** official, EU members only. It gives your own `INBOX` and
     `INVITATIONS`. It is the clean background route.
3. The profile of a person who sends a connect request is not in the DMA data. Route I captures it when you
   open the profile. Manual paste (route C) always works.
4. The account must never get blocked. The rule is: **no heavy traffic, human pace, human session.** See §1.4.
5. The tool is a local web app on `localhost`. It classifies each item, applies a ruleset and writes a
   draft. You edit, copy and send.

## Goal

Save time on LinkedIn messages, but reply to every person with a customized message.

- Show all pending messages and connect requests in one queue.
- Show a pre-written draft next to each item.
- Make the drafts by a **ruleset** that grows over time. Example rules: "decline commercial offers",
  "reply friendly to a connect request and refer to the person's profile".
- Use the "unsolicited decline" custom GPT behavior
  (`https://chatgpt.com/g/g-675c21a3780c8191a1e23c7c1c5fbd93-unsolicited-decline`) and the templates in
  `~/repos/personalNotes/linkedin_starters.md` and
  `~/repos/personalNotes/Career_and_Jobs/gpt_default_prompts_for_answering.md`.

## Non-goals (hard limits)

- **Never send a message automatically.** No send button that talks to LinkedIn. No code that types or
  clicks on linkedin.com.
- No headless browser, no `li_at` cookie in scripts, no Voyager API calls, no third-party SaaS that logs in for you.
- No mass actions: no mass connect, no auto-accept, no outreach campaigns.
- No stealth tooling (fingerprint spoofing, captcha solving). "Look like a human" means: **be** a human
  session at human pace, not hide a bot.

## 1. How to get the data: options and terms

### 1.1 The terms

- LinkedIn User Agreement §8.2 forbids crawlers, bots, browser plug-ins and extensions that "scrape,
  modify the appearance of, or automate activity on" the website. The penalty is restriction or
  closure of the account. Source: [Prohibited software and extensions](https://www.linkedin.com/help/linkedin/answer/a1341387).
- Secondary sources quote a §8.2 bullet against bots that "send or redirect messages". Not checked
  against the agreement text yet.
- Enforcement is mainly by behavior: tools that act like bots (volume, speed, regular timing, headless
  signals) get flagged. The hiQ v. LinkedIn record says LinkedIn restricted over 11 million accounts
  for bot use ([Ninth Circuit, 2019](https://www.fr.com/uploads/4878-hiq-labs-inc-v-linkedin-corp-ninth-circuit-september-9-2019.pdf)).

### 1.2 Option register

| # | Route | Read inbox | Read invitations | Read profiles | Extra traffic | Terms status | Verdict |
|---|---|---|---|---|---|---|---|
| A | **DMA Member Data Portability API** (`r_dma_portability_self_serve`) | yes | yes (6 months) | no | API only, not linkedin.com | **official**, EU/EEA/CH | **Primary, background** |
| B | "Download your data" export (ZIP: `messages.csv`, `Invitations.csv`) | yes | yes | no | none | official | **Fallback, first test data** |
| C | Manual paste into the UI | one thread | one request | yes | none | allowed | **Always on** |
| I | **Passive CDP capture** of the page you have open in your own Chrome | the open thread | the open list | the open profile | **none** | grey (§8.2 "scrape") | **Primary, on demand** (owner decision 2026-10-27) |
| I+ | Active CDP navigation: the tool opens threads/profiles itself | yes | yes | yes | yes, low | grey, higher risk | **Owner decision D2**, hard caps in §1.4 |
| D | Official partner APIs (Messages API, Sales Navigator compliance) | partner only | no | no | — | official, gated | Rejected: not reachable |
| E | Unipile and similar SaaS (headless login on your session) | yes | yes | yes | yes | grey, not a partner | Rejected: session on a third-party server |
| F | `linkedin-api` (tomquirk), other Voyager clients with `li_at` | yes | yes | yes | yes | violates §8.2 (README says so) | Rejected: restriction risk, maybe unmaintained since 2024-11 |
| H | Bot extensions and scraping MCP servers (Waalaxy, Expandi, …) | yes | yes | yes | high | violates §8.2 | Rejected |

### 1.3 Route I in detail: passive capture over CDP

How it works:

1. Start a dedicated Chrome profile with remote debugging, bound to localhost only:
   `google-chrome --user-data-dir=$HOME/.config/linkedin-reply-desk/chrome --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1`.
   (Chrome 136+ refuses remote debugging on the default profile. A dedicated profile is required.)
2. Log in to LinkedIn by hand in that window, once. The session stays in that profile.
3. Browse LinkedIn as usual: open the messaging list, a thread, the invitation manager, a profile.
4. Press "Capture" in the reply desk (or a hotkey). The tool attaches over CDP, reads the DOM text of the
   **current** tab, and detaches. It does not reload, scroll, click or navigate.
5. Parsers turn the page text into items: thread (sender, messages), invitation list (name, headline,
   note), profile (headline, about, positions).

Why this is the safest grey route:

- LinkedIn sees only your own clicks at your own pace. The capture reads what the browser already shows.
- It is a real, visible, logged-in Chrome window, not a headless browser.
- The risk that remains: LinkedIn page scripts could see that a debugger is attached. We do nothing to
  hide it. We keep attach time short (attach, read, detach).

Fragility: LinkedIn changes its HTML often. Parsers read visible text and ARIA roles, not CSS class names.
Each parser has fixture tests on saved, anonymized pages, and a "parse failed" state in the UI (never a
silent empty result).

Firefox: Firefox has a remote agent (WebDriver BiDi) too. v1 uses Chrome because CDP is simpler and the
owner asked for it. Firefox stays the browser for normal use.

### 1.4 Traffic and safety rules (the account must never get blocked)

1. Passive capture (route I) makes **zero** extra requests. Prefer it.
2. Active navigation (route I+) only if the owner enables it (D2). Then:
   - maximum 1 page load per 30–90 s, random gap, never a fixed interval;
   - maximum 40 page loads per day and 10 per session;
   - only while the owner is at the screen (the run starts by a click, never from a timer);
   - stop at once on a login wall, captcha, "unusual activity" page, HTTP 429 or 999. Do not retry.
     Show the stop reason in the UI.
3. Route A calls go to `api.linkedin.com` under an official app. Poll at most once per hour.
4. **Tests never touch LinkedIn.** Unit, integration and e2e tests use saved, anonymized fixtures and a
   fake LinkedIn page server. A live check is manual, one page, behind `LIVE_LINKEDIN=1`.
5. Never send, click "Accept", react or type on linkedin.com from code. Any such code is a defect.

### 1.5 Route A in detail (to verify in the spike)

Sources: [LinkedIn help a6214075](https://www.linkedin.com/help/linkedin/answer/a6214075),
[N. Deville notes](https://notes.nicolasdeville.com/api/linkedin-dma-api/). Treat details as claims.

1. Create an app on developer.linkedin.com. Select the page "Member Data Portability (Member) Default Company".
2. On the Products tab, request "Member Data Portability API (Member)". Access comes with the terms, no review.
3. Get a token with scope `r_dma_portability_self_serve` (3-legged OAuth, redirect `http://localhost:8799/callback`).
4. Call `POST /rest/memberAuthorizations` with `{}` to start the changelog archive.
5. Snapshot: `GET /rest/memberSnapshotData?q=criteria&domain=INBOX&start=N`. Repeat until "No data found".
6. New events: `GET /rest/memberChangeLogs?q=memberAndApplication&startTime=<ms>&count=50`.

Claimed constraints: header `Linkedin-Version: 202312` is mandatory. `INBOX` is ready about 1 h after
consent (`404` before). Pages can repeat rows; `total` is not reliable. The changelog keeps 28 days,
50 events per call, `startTime` is inclusive (deduplicate on `id`). Message events carry URNs, not names.
The token lives 2–12 months, with no refresh token. Open: are new invitations in the changelog? Is
read/unread state in the data? If not, "pending" = the last message is not from you.

### 1.6 What is really known: partners, and what creators and their teams use (2026-10-27)

Confidence key: **[L]** LinkedIn's own text, **[V]** vendor or affiliate blog (a claim, not a fact).

Approved partners:

- Messaging API: "restricted to approved partners", messages only to 1st-degree connections, no automated or scheduled sends **[L, quoted by V]**.
- No public partner list exists. One blog names Hootsuite, Sprinklr, Oktopost, Brandwatch, Zoho Recruit, Bird CRM, but for **Company Page** inboxes, not personal DMs **[V, not verified]**.
- SNAP (Sales Navigator Application Platform) takes no new partners. No form, no waitlist **[V, cites LinkedIn docs]**.
- Partner approval, if open at all: 4 weeks to 4 months **[V]**.
- Result: no partner route reads or answers a **personal** inbox for a single member. The DMA API (route A) is the only official read route.

Delegation:

- Personal profiles have **no delegate role**. Only Company Pages have admin roles **[V, consistent across sources]**.
- The User Agreement forbids sharing an account **[L, via tracker, version 2026-05-05]**.
- Official OAuth lets a team **post** for a member (`w_member_social`), not read or send DMs **[L]**.

How creators and their teams really handle DMs (so the owner does not log in for everything):

| Way | Examples | How it reads DMs | Risk |
|---|---|---|---|
| Shared password, assistant logs in | ghostwriting agencies with "DM management" packages | full session | breaks the account-sharing clause; 2FA prompts go to the owner |
| Cloud tool holds the session (`li_at`, cloud IP or proxy) | HeyReach, Expandi, Unipile-based tools | Voyager calls from a server | §8.2; the most flagged pattern |
| Browser extension in the owner's browser | Kondo (inbox labels, snippets, ~$35/mo), Taplio (hit by the April 2025 enforcement wave) | reads/changes the page | §8.2 names extensions; vendors claim "safe" |
| CRM with unified inbox | Breakcold, LeadDelta | extension or session sync | grey, vendor "safe" ratings without method |
| Content-only tools, official API | Supergrow, AuthoredUp, Kleo, Ordinal, MagicPost | do not read DMs | low; posting only |

What this means for us: the market has no clean "team works the inbox" route. The pattern closest to
safe is **"an assistant prepares, the owner sends from the owner's own session"**. That is this tool.
The assistant is the local app, the session stays in the owner's own Chrome, and nothing leaves the machine
except the LLM call.

Sources: [Phyllo](https://www.getphyllo.com/post/linkedin-api-access-in-2026-partner-program-approval-timeline-alternatives),
[Unipile](https://www.unipile.com/best-linkedin-api/), [linkedapi.io](https://linkedapi.io/guides/how-to-automate-linkedin-messages),
[Kondo comparison](https://www.trykondo.com/blog/linkedin-inbox-software-reviews), [exeedin](https://www.exeedin.com/post/best-linkedin-ghostwriting-ai-tools),
[ghostwriting-ai.com](https://www.ghostwriting-ai.com/comparisons/best-linkedin-ai-tools-for-ghostwriters),
[MagicPost](https://magicpost.in/blog/how-to-manage-multiple-linkedin-accounts), [LigoSocial](https://ligosocial.com/blog/give-someone-access-to-linkedin-without-password),
[ConductAtlas](https://conductatlas.com/platform/linkedin/linkedin-user-agreement/prohibition-on-account-sharing-or-transfer/).

### 1.7 Grey-zone tools: detection and user reports (2026-10-27)

Verdict: no grey tool is a fit. Most are **outreach** bots (they send), which is the pattern LinkedIn hunts.
The automation we need is **reading and drafting**. Route A does the reading officially and in the background.

How LinkedIn detects:

- **Extension scan ("BrowserGate", reported 2026-04):** a ~2.7 MB script probes the
  `web_accessible_resources` of 6,000+ Chrome extension IDs, plus device data (CPU, memory, screen,
  timezone). LinkedIn says it targets extensions that scrape or break the ToS
  ([gHacks](https://www.ghacks.net/2026/04/04/linkedin-uses-hidden-javascript-to-scan-for-over-6000-chrome-extensions-on-visitors-browsers/),
  [Tom's Hardware](https://www.tomshardware.com/software/browsers/linkedin-scans-visitors-browsers-for-over-6000-chrome-extensions-and-collects-device-data),
  [Security Boulevard](https://securityboulevard.com/2026/01/detecting-browser-extensions-for-bot-detection-lessons-from-linkedin-and-castle/)).
- **Behavior:** volume, speed, regular timing, cloud IPs. Voyager logins from cloud IPs get "challenge" pages.
- No official ban statistics exist. The often-quoted "40% restricted in Q1 2026" traces to one unverified source
  ([fact-check](https://www.leadsforlinked.com/blog/linkedin-ban-statistics-fact-check.html)).

| Tool | Type | What users report | Worth it for us? |
|---|---|---|---|
| Kondo | Chrome extension, inbox labels, snippets, no sending | No ban reports found. All safety claims come from Kondo itself. Changes the page look (§8.2 names that). | Maybe, as a stopgap UI. Does not draft per rule. |
| Unipile | API SaaS, holds your session on its server | Re-auth/checkpoint prompts are the recurring complaint. "Safer than browser bots, not risk-free". | No. Session leaves your machine. Built for SaaS vendors. |
| HeyReach | Cloud outreach | LinkedIn removed HeyReach's company page and banned the founder's profile (2026, blog report). | No. Outreach, actively fought. |
| Expandi | Cloud outreach | Mixed: a Reddit-quoted loss of a long-held account; others rank it "most trusted". | No. Outreach. |
| Waalaxy | Extension + cloud outreach | Trustpilot: reach drops / "shadow ban" questions. | No. Outreach. |
| Dux-Soup | Extension outreach | "Old guard, most ban complaints" (Reddit roundup). | No. |
| Linked Helper | Desktop browser outreach | Restricted "despite the recommended daily limits" (Trustpilot). | No. |
| Taplio | Content + extension | Hit by the April 2025 enforcement wave. | No. Posting only. |
| `linkedin-api` (Voyager) | Python, `li_at` login | README: "Linkedin may (and will) ban your account". Challenge on login from cloud IPs. Repo reportedly 404 since 2026-07. | No. |

What this means for route I (our CDP capture):

- It is not an extension, so the extension scan does not see it.
- An attached DevTools session can be detected by known page-script tricks. We do not hide it. We keep it
  read-only, rare and short. This is the residual risk of route I, and the owner accepts it (D5).
- Device data and IP stay your normal ones: it is your own Chrome on your own line.

Sources (more): [Yalc Reddit roundup](https://www.yalc.ai/blog/linkedin-automation-tools-reddit/),
[Kondo review](https://www.salesforge.ai/blog/kondo-review), [Unipile review](https://linkupapi.com/blog-articles/unipile-review),
[Linked Helper Trustpilot](https://pl.trustpilot.com/review/linkedhelper.com), [Waalaxy Trustpilot](https://ca.trustpilot.com/review/waalaxy.com),
[nsandman/linkedin-api](https://github.com/nsandman/linkedin-api), [open-linkedin-api issues](https://github.com/EseToni/open-linkedin-api/issues).
All are vendor, affiliate or single-user claims. None is a measurement.

### 1.8 Automation level (owner: "we need automation", 2026-10-27)

| Step | Automated? | How |
|---|---|---|
| Read new messages and invitations | **yes, fully** | Route A in the background, hourly, official |
| Read profiles of new contacts | on demand, or capped automatic (D2) | Route I capture; I+ only if D2 = yes |
| Classify, apply rules, write drafts | **yes, fully** | LLM + ruleset, as soon as an item arrives |
| Notify | **yes** | Desktop notification: "5 new drafts ready" |
| Send | **never** | Owner: copy, open thread, paste, send |

## 2. Product

### 2.1 Flow

1. **Collect.** Route A syncs in the background (hourly). Route I adds what you capture while you browse.
   Both write to one local SQLite file and merge by thread and person.
2. **Classify.** Each item gets a category: `commercial_offer`, `recruiter`, `connect_request`,
   `personal`, `colleague`, `event_invite`, `other`. The LLM does it, rules can override it.
3. **Draft.** The first matching rule picks the action and the prompt. The LLM writes the draft in the
   sender's language (German or English).
4. **Review.** You open the queue. You edit the draft, then press "Copy and open thread".
5. **Send.** You paste and send in LinkedIn yourself. You mark the item "done", or the next sync sees your reply.
6. **Learn.** If you change a draft a lot, the tool offers "save as rule example". The ruleset grows.

### 2.2 UI (localhost)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ Reply desk  [Capture tab] [Sync API] last 14:02 · 23 pending   filter: [all ▾] │
├──────────────────────────┬────────────────────────────────────────────────────┤
│ ● Anna K.  connect   2h  │ Anna K. · Head of Embedded, ACME · connect request  │
│ ● J. Doe   offer    5h   │ Note: "Hi Marcel, loved your talk on Qt…"           │
│ ● R. Lee   recruiter 1d  │ Profile: captured 13:58 ✓  [show] [paste instead]   │
│ ○ M. Roth  personal  2d  │─────────────────────────────────────────────────────│
│   …                      │ Rule: friendly_connect (#3)   Category: connect ✓   │
│                          │ Draft (DE ▾)  tone: friendly ▾                       │
│                          │ ┌─────────────────────────────────────────────────┐ │
│                          │ │ Hallo Anna, danke für die Anfrage …             │ │
│                          │ └─────────────────────────────────────────────────┘ │
│                          │ [Regenerate] [Copy + open thread] [Done] [Skip]      │
│                          │ [Wrong rule → choose ▾] [Save as rule example]      │
└──────────────────────────┴────────────────────────────────────────────────────┘
```

- **Queue left, detail right.** Sort by age, filter by category and rule.
- **Keyboard first:** `j`/`k` next/previous, `c` copy and open, `d` done, `r` regenerate, `e` edit.
- **Copy + open thread** puts the draft on the clipboard and opens the thread URL (or the invitation
  manager) in the Chrome window. You paste and send there.
- **Capture tab** reads the current Chrome tab (route I). A toast says what it found: "thread with
  Anna K., 4 messages" or "parse failed: unknown page".
- **Profile hint:** for a connect request without a profile, the UI says "open the profile in Chrome,
  then press Capture". The draft regenerates with a personal hook.
- **Why this rule:** every draft shows the rule and the category, and you can change both.
- **Bulk view:** a table of all `commercial_offer` drafts. You check them in one pass, but you still
  send each one yourself.

### 2.3 Ruleset

A YAML file `rules.yaml`, ordered, first match wins. You edit it by hand or from the UI.

```yaml
- id: decline_commercial
  when: { category: commercial_offer }
  action: decline
  prompt: prompts/unsolicited_decline.md   # copy of the custom GPT instructions
  tone: polite, short, no opening for a follow-up
- id: friendly_connect
  when: { category: connect_request }
  action: reply
  prompt: prompts/friendly_connect.md      # uses note + captured profile
  tone: warm, refer to one concrete point of the profile
- id: recruiter_senior_only
  when: { category: recruiter }
  action: reply
  prompt: prompts/recruiter_senior_only.md # from gpt_default_prompts_for_answering.md
- id: fallback
  when: {}
  action: draft_only
  prompt: prompts/generic.md
```

- `when` can also match `keywords`, `sender_title`, `language`, `has_profile`.
- Every rule can have `examples:` (input + your final reply). Few-shot examples make the drafts better.
- One golden test case per rule, so a new rule cannot break an old one.

### 2.4 LLM

- Default: OpenAI API. The custom GPT cannot be called by API, so its instructions move to
  `prompts/unsolicited_decline.md`.
- Option: local Ollama on the box (`192.168.100.67`). The message data then stays on your network.
- The provider is one config value. Tests use a fake provider.

## 3. Architecture

- Python 3.14, FastAPI, Jinja2 + htmx (no SPA build), SQLite, `httpx`, `pydantic`.
- `collect/`: `cdp_capture` (route I, read-only CDP client), `page_parsers/`, `dma_client` (route A),
  `export_import` (route B). `core/`: classify, rules, draft. `web/`: UI.
- The CDP client exposes only read calls (`Runtime.evaluate` of a fixed read script, `DOM` reads).
  A unit test fails if the code contains `Input.dispatch*`, `Page.navigate` (unless I+ is enabled) or a click call.
- Secrets (OAuth token, OpenAI key) and the Chrome profile live in `~/.config/linkedin-reply-desk/`.
- Message data is personal data of third persons. It stays local, never in git, never in logs.

## 4. Owner decisions

| ID | Question | State |
|---|---|---|
| D1 | LLM: OpenAI API, local Ollama, or both? | Open. Default: both, OpenAI first |
| D2 | Allow active navigation (route I+) under the caps in §1.4? | Open. Default: no, passive only |
| D3 | Export the "unsolicited decline" GPT instructions into `prompts/` | Open. Only the owner can read them |
| D4 | Docker | Decided: not now (2026-10-27) |
| D5 | Read route | Decided: route I (Chrome + DevTools, passive) + route A (2026-10-27) |
| D6 | Traffic | Decided: no heavy traffic, human pace, careful with all requests and tests (2026-10-27) |
