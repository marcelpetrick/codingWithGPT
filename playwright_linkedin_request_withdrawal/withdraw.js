const { chromium } = require('playwright');

const MAX_WITHDRAWALS = 10;

function log(msg, meta = {}) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${msg}`, meta);
}

function randomDelay(min = 1000, max = 3000) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function sleep(page, label = '') {
  const delay = randomDelay();
  log(`sleep ${label}`, { delay });
  await page.waitForTimeout(delay);
}

// ---------- CORE ----------

async function waitForPageReady(page) {
  log('Waiting for invitation list (robust mode)');

  // Wait for main container
  await page.waitForSelector('text=Manage invitations', { timeout: 15000 });

  // Force render
  await page.mouse.wheel(0, 2000);
  await page.waitForTimeout(1500);

  // Wait until ANY visible button contains withdraw text
  await page.waitForFunction(() => {
    const buttons = Array.from(document.querySelectorAll('button'));

    return buttons.some(btn => {
      const text = btn.textContent || '';
      return text.includes('Withdraw') || text.includes('Zurückziehen');
    });
  }, { timeout: 15000 });

  log('Invitation list ready');
}

async function findWithdrawButtons(page) {
  const buttons = page.locator('button');

  const result = [];
  const count = await buttons.count();

  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i);

    const text = await btn.textContent().catch(() => '');

    if (!text) continue;

    if (text.includes('Withdraw') || text.includes('Zurückziehen')) {
      result.push(btn);
    }
  }

  log('Filtered withdraw buttons', { found: result.length });

  return result;
}

async function withdrawOne(page) {
  const buttons = await findWithdrawButtons(page);

  if (buttons.length === 0) {
    log('No withdraw buttons found');
    return false;
  }

  const btn = buttons[0];

  try {
    log('Click withdraw');

    await btn.scrollIntoViewIfNeeded();
    await btn.click();

    await sleep(page, 'after click');

    // confirm button (same label, appears last)
    const confirmButtons = await findWithdrawButtons(page);

    const confirm = confirmButtons[confirmButtons.length - 1];

    log('Click confirm');

    await confirm.click();

    await sleep(page, 'after confirm');

    return true;

  } catch (err) {
    log('Withdraw failed', { error: err.message });
    return false;
  }
}

// ---------- MAIN ----------

(async () => {
  const browser = await chromium.launch({
    headless: false,
    slowMo: 200
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    log('Opening login');
    await page.goto('https://www.linkedin.com/login');

    log('Login manually, then press ENTER');
    await new Promise(resolve => process.stdin.once('data', resolve));

    log('Go to sent invites');
    await page.goto('https://www.linkedin.com/mynetwork/invitation-manager/sent/');

    await waitForPageReady(page);

    let success = 0;

    while (success < MAX_WITHDRAWALS) {
      log('Attempt', { success });

      const ok = await withdrawOne(page);

      if (!ok) break;

      success++;

      await page.mouse.wheel(0, 1200);
      await sleep(page, 'between');

      if (success % 5 === 0) {
        log('Cooldown');
        await page.waitForTimeout(5000);
      }
    }

    log('Done', { success });

  } catch (err) {
    log('Fatal error', { error: err.message });
  }
})();
