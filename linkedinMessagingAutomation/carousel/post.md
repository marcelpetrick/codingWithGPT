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

## Version 2: status codes (`v2_status_codes.pdf`, 7 slides) — chosen

Written after the owner's blog posts (marcelpetrick.bplaced.net/wp_solutionsnotcode, October 2026):
situation first, `..`, "you know the drill", serif bold for key terms, a wink at the end.
Wording: the owner **thought about** automating; nothing was tried.

```
I get a lot of messages on LinkedIn. Connect requests, recruiters, and of course the "quick call about your lead generation?" offers. Answering all of them in a friendly and individual way takes time. So I thought about automating it .. at least partly.

But before writing the first line of code: what is allowed at all? As a developer I also always wondered how influencers and their teams handle this. I doubt they type every comment and react to every message by hand.

So I gathered information: terms of use, APIs, lawsuits, user reports. Quite a rabbit hole. Result: LinkedIn is 𝐩𝐢𝐜𝐤𝐲 about it.

The short version, in HTTP status codes (you know the drill):
* 𝟐𝟎𝟎: posting via the API works
* 𝟒𝟎𝟑: DMs only for approved partners. No form, no waitlist.
* 𝟗𝟗𝟗: LinkedIn's own status code for bots. Not in any RFC ;)
* 𝟒𝟓𝟏 and 𝟒𝟏𝟎: lawsuits against scrapers and removed company pages of tool vendors, in 2025 and 2026

Details in the carousel, sources in the first comment.

So if I build something, then like this: a local tool reads and prepares the drafts. Sending stays my job.

If you know more, tell me. Of course, this is no legal advice 😉
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
