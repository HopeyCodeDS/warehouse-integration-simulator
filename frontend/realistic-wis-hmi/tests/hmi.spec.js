import { test, expect } from '@playwright/test';

test.describe('Realistic WIS HMI', () => {
  test('renders the complete fleet and switches between spatial projections', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.robot-2d')).toHaveCount(4);
    await expect(page.locator('.robot-2d strong')).toHaveText(['AMR-Ultra', 'AMR-Nova', 'AMR-Orbit', 'AMR-Vega']);

    await page.getByRole('button', { name: /3D Twin/ }).click();
    await expect(page.locator('canvas')).toHaveCount(1);
    await expect.poll(async () => page.locator('canvas').evaluate((canvas) => ({
      width: canvas.width,
      height: canvas.height,
      dataLength: canvas.toDataURL('image/png').length,
    }))).toMatchObject({ width: expect.any(Number), height: expect.any(Number) });
    await expect.poll(async () => page.locator('canvas').evaluate((canvas) => canvas.toDataURL('image/png').length)).toBeGreaterThan(1_000);
  });

  test('shows a real dispatch response instead of a local-only queue update', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Customer').fill('Playwright Test');
    await page.getByLabel('SKU').selectOption('P200');
    await page.getByLabel('Qty').fill('1');
    await page.getByRole('button', { name: /RELEASE ORDER/ }).click();
    await expect(page.locator('.dispatch-message')).toContainText(/accepted by ERP|rejected|Insufficient stock|failed/i);
  });
});
