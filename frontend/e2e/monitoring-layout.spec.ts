import { expect, test } from '@playwright/test'

test('monitoring page renders the redesigned live monitoring workspace', async ({ page, request }) => {
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

  await page.goto('/monitoring')

  await expect(page.locator('header').getByText('Monitoring', { exact: true })).toBeVisible()
  await expect(page.getByTestId('monitoring-hero')).toBeVisible()
  await expect(page.getByTestId('monitoring-chart-panel')).toBeVisible()
  await expect(page.getByTestId('monitoring-detail-panel')).toBeVisible()
  await expect(page.getByText('Chart Workspace')).toBeVisible()
  await expect(page.getByText('세션 상세')).toBeVisible()
  await expect(page.getByRole('button', { name: '수동 재평가' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '이벤트 로그' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '전략 해설' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '신호' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '주문' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '리스크' })).toBeVisible()
})
