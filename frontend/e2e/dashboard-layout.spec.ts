import { expect, test } from '@playwright/test'

test('dashboard renders the redesigned strategy arena sections', async ({ page, request }) => {
  const sessionResponse = await request.post('http://127.0.0.1:8012/api/v1/sessions', {
    data: {
      mode: 'PAPER',
      strategy_version_id: 'stv_seed_ob_fvg_001',
      symbol_scope: {
        symbols: ['KRW-XRP'],
      },
    },
  })

  expect(sessionResponse.ok()).toBeTruthy()

  await page.goto('/')

  await expect(page.locator('header').getByText('COIN LAB', { exact: true })).toBeVisible()
  await expect(page.locator('header').getByText('Dashboard', { exact: true })).toBeVisible()
  await expect(page.locator('header').getByText('Monitoring', { exact: true })).toBeVisible()
  await expect(page.getByTestId('dashboard-hero')).toBeVisible()
  await expect(page.getByTestId('dashboard-performance-history')).toBeVisible()
  await expect(page.getByTestId('dashboard-live-activity')).toBeVisible()
  await expect(page.getByTestId('dashboard-trades')).toBeVisible()
  await expect(page.getByTestId('dashboard-leaderboard')).toBeVisible()
  await expect(page.getByTestId('dashboard-strategy-grid')).toBeVisible()
  await expect(page.getByTestId('dashboard-market-details')).toBeVisible()

  const strategyCard = page.getByText('XRP OB+FVG Bull Reclaim').first()
  await expect(strategyCard).toBeVisible()
  await expect(page.getByText('실시간 진입률').first()).toBeVisible()
  await expect(page.getByText('모니터링 중').first()).toBeVisible()
  await expect(page.getByRole('button', { name: '모니터링 열기' })).toBeVisible()
})
