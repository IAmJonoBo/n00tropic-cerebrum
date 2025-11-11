import { test, expect } from '@playwright/test'

test('homepage has heading', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toHaveText(/It works/)
})
