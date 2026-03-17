const { chromium } = require('playwright');

function randomDelay(min = 1000, max = 3000) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

(async () => {
  const browser = await chromium.launch({
    headless: false, // keep visible for login + safety
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  console.log("Opening LinkedIn login...");
  await page.goto('https://www.linkedin.com/login');

  console.log("Please log in manually, then press ENTER here...");
  await new Promise(resolve => process.stdin.once('data', resolve));

  console.log("Navigating to sent invitations...");
  await page.goto('https://www.linkedin.com/mynetwork/invitation-manager/sent/');

  await page.waitForLoadState('networkidle');

  let totalWithdrawn = 0;

  while (true) {
    const buttons = await page.locator('button:has-text("Withdraw")');
    const count = await buttons.count();

    if (count === 0) {
      console.log("No more invitations found.");
      break;
    }

    console.log(`Found ${count} withdraw buttons...`);

    // Always operate on the first visible button
    const btn = buttons.first();

    try {
      await btn.scrollIntoViewIfNeeded();
      await btn.click();

      await page.waitForTimeout(randomDelay());

      // Confirm dialog button
      const confirm = page.locator('button:has-text("Withdraw")').last();

      await confirm.click();

      totalWithdrawn++;
      console.log(`Withdrawn: ${totalWithdrawn}`);

      await page.waitForTimeout(randomDelay());

    } catch (err) {
      console.log("Error occurred, retrying...", err.message);
      await page.waitForTimeout(2000);
    }

    // Small safety: stop after a batch to avoid flags
    if (totalWithdrawn % 20 === 0) {
      console.log("Cooling down for 10 seconds...");
      await page.waitForTimeout(10000);
    }
  }

  console.log(`Done. Total withdrawn: ${totalWithdrawn}`);

  // await browser.close(); // optional
})();
