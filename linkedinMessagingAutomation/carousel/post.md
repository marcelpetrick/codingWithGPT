# LinkedIn posts for the two carousels

Upload the PDF as a "document" post. Put the sources in the first comment (links in a PDF are not clickable
on LinkedIn). Facts and confidence: `../research/automation_crackdown_2025_2026.md`.

## Version 1: timeline (`v1_timeline.pdf`, 9 slides)

```
As a developer, I always wondered: do influencers and their teams really type every reply and every reaction by hand?

I wanted to automate my own LinkedIn inbox. So I checked what LinkedIn allows, and what it did in 2025 and 2026 to tools that went further.

Three things surprised me:
→ The API lets you post. Sending DMs is for approved partners only.
→ A scraper with a ~$10M business was gone five months after LinkedIn sued.
→ LinkedIn checks browsers for 6,000+ extensions. In 2017 it was 38.

9 slides. Sources in the first comment.

#LinkedIn #Automation #SoftwareDevelopment #API #Privacy
```

## Version 2: status codes (`v2_status_codes.pdf`, 7 slides)

```
I tried to automate my LinkedIn inbox. LinkedIn answered with status codes.

200: posting works.
403: DMs are for partners only.
999: LinkedIn's own code for bots.
451: two scraper companies in court in 2025.
410: company pages of tool vendors, gone.

What I do now: a local tool reads and drafts. I send every reply myself.

7 slides, facts from 2025 and 2026. Sources in the first comment.

#LinkedIn #Developers #API #Automation #HTTP
```

### Version 2, short

```
I tried to automate my LinkedIn inbox. LinkedIn answered in HTTP status codes 🙂

200 for posting. 403 for DMs. And 999 for bots, a code LinkedIn invented itself.

So my tool reads and drafts, and I still send every reply myself.

Sources in the first comment.

#LinkedIn #Developers #API #Automation
```

## First comment (both versions)

```
Sources:
• LinkedIn: prohibited software (User Agreement 8.2) https://www.linkedin.com/help/linkedin/answer/a1341387
• LinkedIn: member portability APIs (EU) https://www.linkedin.com/help/linkedin/answer/a6214075
• LinkedIn Community Report, H2 2025 https://about.linkedin.com/transparency/community-report
• Proxycurl suit and settlement https://www.socialmediatoday.com/news/linkedin-wins-legal-case-data-scrapers-proxycurl/756101/
• Proxycurl founder: "Goodbye Proxycurl" https://nubela.co/blog/goodbye-proxycurl/
• ProAPIs suit https://news.bloomberglaw.com/ip-law/linkedin-battles-online-scrapers-in-perpetual-struggle-over-data
• ProAPIs suit https://therecord.media/linkedin-sues-data-scraping-company
• Apollo page removed https://salesmotion.io/blog/linkedin-removed-apollo-brand-page-2025-alternatives
• HeyReach, own account https://www.heyreach.io/blog/heyreach-ban
• BrowserGate https://www.ghacks.net/2026/04/04/linkedin-uses-hidden-javascript-to-scan-for-over-6000-chrome-extensions-on-visitors-browsers/
• BrowserGate https://www.tomshardware.com/software/browsers/linkedin-scans-visitors-browsers-for-over-6000-chrome-extensions-and-collects-device-data
• HTTP 999 https://http.dev/999
• "40% banned" fact-check https://www.leadsforlinked.com/blog/linkedin-ban-statistics-fact-check.html
```
