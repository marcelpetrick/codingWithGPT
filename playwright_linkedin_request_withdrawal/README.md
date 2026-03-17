# LinkedIn Sent Invitation Cleanup (Playwright)

## Purpose

This project automates the withdrawal of **sent connection requests** on LinkedIn via browser automation using Playwright.

LinkedIn does not provide an official API for managing sent invitations. This script replicates user interactions in the browser UI to withdraw pending requests in a controlled, rate-limited way.

---

## ⚠️ Disclaimer

- This script interacts with the LinkedIn UI and is **not officially supported** by LinkedIn.
- Automated usage may violate LinkedIn's Terms of Service.
- Use at your own risk.
- Keep usage **low-volume and human-like** to reduce the risk of account restrictions.

---

## Features

- Withdraws **up to 10 sent invitations per run**
- Randomized delays (1–3 seconds) to mimic human behavior
- Structured logging with timestamps
- Safe stop conditions (no infinite loops)
- Works with **English and German UI**

---

## Requirements

- Linux (tested on Manjaro, should work on most distros)
- Node.js (recommended: **v20 LTS**)
- npm

---

## Installation

### 1. Install Node (recommended via fnm)

```bash
sudo pacman -S fnm
````

Add to your shell config (`~/.zshrc` or `~/.bashrc`):

```bash
eval "$(fnm env --use-on-cd)"
```

Reload shell:

```bash
exec zsh
```

Install Node:

```bash
fnm install 20
fnm use 20
fnm default 20
```

Verify:

```bash
node -v
npm -v
```

---

### 2. Install project dependencies

```bash
npm install
```

Install Playwright browser:

```bash
npx playwright install chromium
```

---

### 3. Install system dependencies (if needed)

If Playwright fails to launch Chromium:

```bash
sudo pacman -S nss gtk3 libx11 libxcomposite libxdamage libxrandr libgbm pango alsa-lib
```

---

## Usage

Run the script:

```bash
node withdraw.js
```

### Workflow

1. A browser window opens
2. Log into your LinkedIn account manually
3. Return to the terminal and press **ENTER**
4. The script:

   * navigates to sent invitations
   * withdraws up to 10 requests
   * logs each action
   * exits safely

---

## Behavior

* Withdraws **max 10 invitations per run**
* Adds **random delays (1–3 seconds)** between actions
* Adds light scrolling to trigger lazy loading
* Stops automatically if:

  * no more invitations are found
  * an error occurs repeatedly

---

## Logging

Example output:

```
[2026-03-17T12:00:00.000Z] Withdrawal attempt { attempt: 1, successCount: 0 }
[2026-03-17T12:00:02.123Z] Withdrawal successful { successCount: 1 }
```

Logs include:

* timestamps
* attempt counters
* success tracking
* error messages

---

## Configuration

You can adjust behavior in `withdraw.js`:

```js
const MAX_WITHDRAWALS = 10;
const MIN_DELAY = 1000;
const MAX_DELAY = 3000;
```

---

## Known Limitations

* Relies on LinkedIn UI → may break if UI changes
* Button text is language-dependent (currently supports EN/DE)
* Requires manual login (no session persistence by default)

---

## Safety Recommendations

* Do not run repeatedly in short intervals
* Keep total withdrawals low per day
* Avoid running multiple instances in parallel
* Keep browser visible (non-headless) for transparency

---

## Troubleshooting

### Script does nothing

* Ensure you pressed ENTER after login
* Check if you are on the correct LinkedIn page

### No buttons found

* UI language mismatch → update selectors in code

### Chromium fails to launch

* Install missing system libraries (see above)
