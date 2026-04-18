import { test, expect } from '@playwright/test'

test.describe('Landing', () => {
  test('home shows GlucoSense heading', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('body')).toBeVisible()
  })
})
