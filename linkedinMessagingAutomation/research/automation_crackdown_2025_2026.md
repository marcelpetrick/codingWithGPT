# LinkedIn automation and the crackdown, 2025–2026

Research dossier, 2026-10-27. It holds every fact used in the carousels in `../carousel/`, with source
and confidence. The project decisions that follow from it are in `../vision.md` §1.

Confidence key:

- **[L]** LinkedIn's own text (help center, transparency report, court filing).
- **[P]** independent press (Bloomberg Law, The Record, Tom's Hardware, gHacks, Social Media Today).
- **[V]** vendor, competitor or affiliate blog. A claim, not a fact.
- **[1]** one source only.

## Verdict

1. LinkedIn fights automation on three levels in 2025–2026: **courts** (scraper companies), **brand pages**
   (tool vendors lose their company page) and **detection** (extension scan, device data, behavior).
2. The official API lets you post for a member. It does not let you read or send DMs, except for approved
   partners. EU members can read their own inbox through the DMA portability API, read-only.
3. No reliable ban rate exists. The common "40%" figure traces back to one unverified source.
4. Teams of creators therefore use shared logins, cloud session tools or extensions. All three are grey.

## 1. What is officially possible

| Fact | Conf. | Source |
|---|---|---|
| Third-party software, bots and browser extensions that scrape, modify the look of, or automate linkedin.com are not permitted (User Agreement §8.2). Penalty: restriction or closure. | L | [LinkedIn help a1341387](https://www.linkedin.com/help/linkedin/answer/a1341387) |
| The Messaging API is restricted to approved partners, only to 1st-degree connections, no automated or scheduled sends. | L via V | [linkedapi.io](https://linkedapi.io/guides/how-to-automate-linkedin-messages), [Swarmhit](https://www.swarmhit.com/blog/linkedin-messaging-api) |
| No public partner list. Sales Navigator partner program (SNAP) takes no new partners. | V | [Phyllo](https://www.getphyllo.com/post/linkedin-api-access-in-2026-partner-program-approval-timeline-alternatives), [Unipile](https://www.unipile.com/best-linkedin-api/) |
| Self-serve API: sign-in and `w_member_social` (post, comment, react for a member). No inbox scope. | V (consistent) | [linkedapi.io](https://linkedapi.io/guides/linkedin-api-access) |
| Personal profiles have no delegate role. Company Pages have admin roles. | V (consistent) | [LigoSocial](https://ligosocial.com/blog/give-someone-access-to-linkedin-without-password) |
| The User Agreement forbids sharing an account (version 2026-05-05). | L via tracker | [ConductAtlas](https://conductatlas.com/platform/linkedin/linkedin-user-agreement/prohibition-on-account-sharing-or-transfer/) |
| EU/EEA/CH members can let an app read their own data (DMA Member Data Portability API). `INBOX` and `INVITATIONS` are domains. Read-only. | L + V | [LinkedIn help a6214075](https://www.linkedin.com/help/linkedin/answer/a6214075), [N. Deville](https://notes.nicolasdeville.com/api/linkedin-dma-api/) |
| HTTP `999 Request Denied` is LinkedIn's non-standard code for suspected bots (user agent, request volume). | P/V | [http.dev](https://http.dev/999), [UptimeRobot](https://uptimerobot.com/blog/999-status-code) |

## 2. Timeline 2025–2026

| Date | Event | Conf. | Source |
|---|---|---|---|
| 2025-01-24 | LinkedIn sues Nubela (Proxycurl), N.D. Cal. 3:25-cv-00828. Claim: hundreds of thousands of fake accounts, millions of profiles scraped. | P | [Social Media Today](https://www.socialmediatoday.com/news/linkedin-wins-legal-case-data-scrapers-proxycurl/756101/), [Yahoo Finance](https://finance.yahoo.com/news/linkedin-wins-legal-case-against-162510557.html) |
| 2025-03-07 | Company pages of Apollo.io and Seamless.AI removed. No public reason. Apollo: "does not disrupt Apollo's services". Apollo's page is live again by mid-2026. | V (consistent) | [Salesmotion](https://salesmotion.io/blog/linkedin-removed-apollo-brand-page-2025-alternatives), [LeadGenius](https://www.leadgenius.com/resources/linkedins-b2b-data-crackdown-what-changed-by-2026), [Klue](https://klue.com/newsletter/linkedin-bans-apollo-io) |
| 2025-07-04 | Proxycurl shuts down. Founder: a "~$10M revenue business", closed to comply with the settlement. Permanent injunction: delete the data, stop access. | founder + P | [Nubela: Goodbye Proxycurl](https://nubela.co/blog/goodbye-proxycurl/), [Social Media Today](https://www.socialmediatoday.com/news/linkedin-wins-legal-case-data-scrapers-proxycurl/756101/) |
| 2025-10 | LinkedIn sues ProAPIs. Claim: millions of fake accounts; customers paid up to $15,000/month; the company creates "hundreds if not thousands" of fake accounts daily; LinkedIn detects scraping "within hours". | P | [Bloomberg Law](https://news.bloomberglaw.com/ip-law/linkedin-battles-online-scrapers-in-perpetual-struggle-over-data), [The Record](https://therecord.media/linkedin-sues-data-scraping-company), [TechStrong](https://techstrong.ai/articles/linkedin-sues-company-over-alleged-massive-data-scraping-operation/) |
| 2025 H2 | Community Report: 99.7% of fake accounts stopped before any member report; automated defenses blocked 97.8% of them; 98.6% of removed spam/scam stopped automatically. | L | [LinkedIn Community Report](https://about.linkedin.com/transparency/community-report) |
| 2026-03-25 | HeyReach (cloud outreach tool): company page removed (~16,400 followers); CEO, CTO, CRO, CMO profiles restricted (HeyReach: "temporarily"). Customer campaigns kept running. No reason published. | vendor + V | [HeyReach](https://www.heyreach.io/blog/heyreach-ban), [Valley](https://joinvalley.co/blog/linkedin-automation-safety-2026) |
| 2026-04 | "BrowserGate": a ~2.7 MB script probes 6,000+ Chrome extension IDs (about 38 in 2017, ~461 in 2024, ~2,000 in 2025) and reads CPU cores, memory, screen, timezone, battery. LinkedIn: it detects extensions that scrape or break the ToS. | P | [gHacks](https://www.ghacks.net/2026/04/04/linkedin-uses-hidden-javascript-to-scan-for-over-6000-chrome-extensions-on-visitors-browsers/), [Tom's Hardware](https://www.tomshardware.com/software/browsers/linkedin-scans-visitors-browsers-for-over-6000-chrome-extensions-and-collects-device-data), [Security Boulevard](https://securityboulevard.com/2026/01/detecting-browser-extensions-for-bot-detection-lessons-from-linkedin-and-castle/) |
| 2026-04-07 | Class action against LinkedIn over the scan (wiretap law), California. | 1 | [State of Surveillance](https://stateofsurveillance.org/news/linkedin-browsergate-scanning-6000-extensions-surveillance-lawsuit-2026/) |

## 3. Myths

| Claim | Status | Source |
|---|---|---|
| "40% of automation accounts were restricted in Q1 2026" | Traces to one source. LinkedIn publishes no such statistic. | [leadsforlinked fact-check](https://www.leadsforlinked.com/blog/linkedin-ban-statistics-fact-check.html) |
| "LinkedIn sent HeyReach a cease-and-desist" | Unverified. | same |
| "Cloud tools are safe" / "extensions are safe" | Each camp says the other gets banned. Both are vendors. | [Yalc](https://www.yalc.ai/blog/linkedin-automation-tools-reddit/), [northlight](https://northlight.ai/blog/linkedin-automation-without-getting-banned) |

## 4. How creators' teams work in practice

| Way | Examples | Risk |
|---|---|---|
| Shared password | ghostwriting agencies with "DM management" | breaks account-sharing clause; 2FA goes to the owner |
| Cloud tool holds the session | HeyReach, Expandi, Unipile-based tools | §8.2; vendor itself hit in 2026 |
| Browser extension | Kondo, Waalaxy, Dux-Soup, Taplio | §8.2 names extensions; 6,000+ IDs scanned |
| Official API | Supergrow, AuthoredUp, Ordinal (posting) | low, but no DMs |

Sources: [MagicPost](https://magicpost.in/blog/how-to-manage-multiple-linkedin-accounts), [Kondo comparison](https://www.trykondo.com/blog/linkedin-inbox-software-reviews), [ghostwriting-ai.com](https://www.ghostwriting-ai.com/comparisons/best-linkedin-ai-tools-for-ghostwriters), [exeedin](https://www.exeedin.com/post/best-linkedin-ghostwriting-ai-tools).

## 5. Not used in the carousels (too weak)

- "Taplio hit by the April 2025 enforcement wave": one vendor blog.
- Ban timelines "3–7 days" for Voyager scripts: vendor blogs.
- Reddit quotes on Expandi/Dux-Soup bans: only second-hand through vendor roundups.
