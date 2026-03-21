import { expect, test } from '@playwright/test'

test('plugin metadata catalog drives plugin strategy create and detail flow', async ({ page }) => {
  const uniqueSuffix = Date.now()

  await page.goto('/strategies/new')
  await expect(page.getByRole('heading', { name: '전략 생성' })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'JSON Editor' })).toBeVisible()
  await expect(page.getByRole('tab', { name: 'Validation' })).toBeVisible()

  await page.getByRole('combobox').first().click()
  await page.getByRole('option', { name: '플러그인' }).click()

  await page.getByRole('tab', { name: '플러그인 설정' }).click()
  await page.getByRole('combobox').first().click()
  await expect(page.getByRole('option', { name: 'Breakout V1' })).toBeVisible()
  await expect(page.getByRole('option', { name: 'SMC Confluence V1' })).toBeVisible()
  await expect(page.getByRole('option', { name: 'OB FVG Bull Reclaim V1' })).toBeVisible()
  await page.getByRole('option', { name: 'OB FVG Bull Reclaim V1' }).click()

  await expect(page.getByText('1H 상승 구조를 필터로 두고, 15m 상승 임펄스에서 형성된 OB+FVG 되돌림')).toBeVisible()
  await expect(page.locator('label').filter({ hasText: '상위 추세 타임프레임' })).toBeVisible()
  await expect(page.getByText('Bull Mode 이탈 손실 청산')).toBeVisible()
  await expect(page.getByLabel('플러그인 버전')).toHaveValue('1.0.0')

  await page.getByRole('tab', { name: '기본 정보' }).click()
  await page.getByLabel('전략 키').fill(`ob_fvg_e2e_${uniqueSuffix}`)
  await page.getByLabel('전략명').fill(`OB FVG E2E ${uniqueSuffix}`)
  await page.getByRole('button', { name: '전략 생성' }).click()

  await page.waitForURL(/\/strategies\/[^/]+$/)
  await expect(page.getByText('플러그인 요약')).toBeVisible()
  await expect(page.getByText('OB FVG Bull Reclaim V1')).toBeVisible()
  await expect(page.locator('p').filter({ hasText: 'ob_fvg_bull_reclaim_v1' }).first()).toBeVisible()
  await expect(page.locator('p,span').filter({ hasText: '상위 추세 타임프레임' }).first()).toBeVisible()
})
