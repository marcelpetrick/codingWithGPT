const { chromium } = require('playwright');

const MAX_WITHDRAWALS = 10;
const MIN_DELAY = 1000;
const MAX_DELAY = 3000;

// ---------- utilities ----------

function log(msg, meta = {}) {
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${msg}`, Object.keys(meta).length ? meta : '');
}

function randomDelay(min = MIN_DELAY, max = MAX_DELAY) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function sleep(page, label = 'sleep') {
  const delay = randomDelay();
  log(`Sleeping (${label})`, { delay });
  await page.waitForTimeout(delay);
}

// ---------- core actions ----------

async function waitForLogin(page) {
  log('Opening login page');
  await page.goto('https://www.linkedin.com/login');

  log('Waiting for manual login (press ENTER)');
  await new Promise(resolve => process.stdin.once('data', resolve));

  log('Login confirmed');
}

async function navigateToInvites(page) {
  log('Navigating to sent invitations page');
  await page.goto('https://www.linkedin.com/mynetwork/invitation-manager/sent/');
  await page.waitForLoadState('networkidle');

  log('Page loaded');
}

async function getWithdrawButtons(page) {
  const locator = page.locator(
    'button:has-text("Withdraw"), button:has-text("Zurückziehen")'
  );

  const count = await locator.count();
  log('Detected withdraw buttons', { count });

  return { locator, count };
}

async function clickWithdraw(page, buttonLocator) {
  log('Clicking withdraw button');

  await buttonLocator.scrollIntoViewIfNeeded();
  await buttonLocator.click();

  await sleep(page, 'after withdraw click');

  // confirm modal
  const confirm = page.locator(
    'button:has-text("Withdraw"), button:has-text("Zurückziehen")'
  ).last();

  log('Confirming withdrawal');

  await confirm.click();

  await sleep(page, 'after confirm');
}

async function withdrawOne(page) {
  const { locator, count } = await getWithdrawButtons(page);

  if (count === 0) {
    log('No withdraw buttons found');
    return false;
  }

  const btn = locator.first();

  try {
    await clickWithdraw(page, btn);
    return true;
  } catch (err) {
    log('Withdrawal failed', { error: err.message });
    return false;
  }
}

// ---------- main control flow ----------

(async () => {
  log('Launching browser');

  const browser = await chromium.launch({
    headless: false,
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await waitForLogin(page);
    await navigateToInvites(page);

    let successCount = 0;
    let attempts = 0;

    while (successCount < MAX_WITHDRAWALS) {
      attempts++;

      log('Withdrawal attempt', { attempt: attempts, successCount });

      const success = await withdrawOne(page);

      if (!success) {
        log('Stopping: no more actionable items or repeated failure');
        break;
      }

      successCount++;

      log('Withdrawal successful', { successCount });

      await sleep(page, 'between iterations');

      // light scroll to trigger lazy loading
      await page.mouse.wheel(0, 1500);
    }

    log('Run complete', {
      totalAttempts: attempts,
      successfulWithdrawals: successCount,
      maxAllowed: MAX_WITHDRAWALS,
    });

  } catch (err) {
    log('Fatal error', { error: err.message });
  }

  // keep browser open for inspection
  log('Script finished (browser left open)');
})();
