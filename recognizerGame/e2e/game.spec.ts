import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('starts a medium game, finds a match, and keeps the timer visible', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByRole('button', { name: '20 cards' }).click()
  await page.getByRole('button', { name: /start timed challenge/i }).click()

  await expect(page.getByLabel('Your current card')).toBeVisible()
  await expect(page.getByLabel('Next card')).toBeVisible()
  await expect(page.getByLabel('Elapsed time')).toBeVisible()
  await expect(page.getByText('0 of 19 matches')).toBeVisible()

  const currentLabels = await page
    .getByLabel('Your current card')
    .getByRole('button')
    .evaluateAll((buttons) =>
      buttons.map((button) => button.getAttribute('aria-label')),
    )
  const nextLabels = new Set(
    await page
      .getByLabel('Next card')
      .getByRole('button')
      .evaluateAll((buttons) =>
        buttons.map((button) => button.getAttribute('aria-label')),
      ),
  )
  const matchingLabel = currentLabels.find((label) => nextLabels.has(label))

  expect(matchingLabel).toBeTruthy()
  await page.getByRole('button', { name: matchingLabel! }).first().click()
  await expect(page.getByText('1 of 19 matches')).toBeVisible()
})

test('main menu has no automatically detectable accessibility violations', async ({
  page,
}) => {
  await page.goto('/')
  const results = await new AxeBuilder({ page }).analyze()
  expect(results.violations).toEqual([])
})
