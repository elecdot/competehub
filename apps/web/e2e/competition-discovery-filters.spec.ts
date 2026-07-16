import { expect, test } from './fixtures/actors'

test.use({ actorName: 'student' })

test('keeps discovery compact and progressively reveals guided filters', async ({
  actorPage,
}, testInfo) => {
  await actorPage.goto('/competitions')

  const advancedFilters = actorPage.getByTestId('advanced-filters')
  await expect(advancedFilters).toBeHidden()

  const firstResult = actorPage.getByRole('heading', {
    name: 'Seeded University Innovation Challenge 2025',
  })
  await expect(firstResult).toBeVisible()
  if (testInfo.project.name === 'mobile-chromium') {
    const box = await firstResult.boundingBox()
    const viewport = actorPage.viewportSize()
    expect(box).not.toBeNull()
    expect(viewport).not.toBeNull()
    expect(box!.y).toBeLessThan(viewport!.height)
  }

  await actorPage.getByRole('button', { name: '更多筛选' }).click()
  await expect(advancedFilters).toBeVisible()

  await actorPage.getByTestId('filter-category').click()
  const options = actorPage.locator('.ant-select-dropdown:visible')
  const innovationOption = options
    .locator('.ant-select-item-option-content')
    .filter({ hasText: 'innovation' })
  await expect(innovationOption).toBeVisible()
  await innovationOption.click()
  await actorPage.locator('form[aria-label="赛事筛选"] button[type="submit"]').click()

  await expect(actorPage).toHaveURL('/competitions?category=innovation')
  await expect(advancedFilters).toBeVisible()
  await expect(firstResult).toBeVisible()

  await actorPage.getByRole('button', { name: '重置' }).click()
  await expect(actorPage).toHaveURL('/competitions')
  await expect(advancedFilters).toBeHidden()
})

test('opens advanced filters for deep links and recoverable deadline errors', async ({
  actorPage,
}) => {
  await actorPage.goto('/competitions?major=软件工程')

  const advancedFilters = actorPage.getByTestId('advanced-filters')
  await expect(advancedFilters).toBeVisible()
  await expect(actorPage.getByTestId('filter-major')).toContainText('软件工程')

  await actorPage.goto('/competitions?deadline_from=2099-12-01&deadline_to=2099-01-01')
  await expect(advancedFilters).toBeVisible()
  await expect(actorPage.getByRole('alert')).toContainText('开始日期不能晚于结束日期')

  await actorPage.getByRole('button', { name: '重置' }).click()
  await expect(actorPage).toHaveURL('/competitions')
  await expect(advancedFilters).toBeHidden()
})

test.describe('filter option failure recovery', () => {
  test.use({ allowDiscoveryRequestErrors: true })

  test('keeps deep-link recovery and keyword discovery usable when guided options fail', async ({
    actorPage,
  }) => {
    await actorPage.route('**/api/v1/competitions/filter-options', async (route) => {
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' })
    })

    await actorPage.goto('/competitions?category=innovation')
    await expect(actorPage.getByTestId('filter-options-error')).toContainText(
      '更多筛选选项暂时无法加载',
    )

    const categoryFilter = actorPage.getByTestId('filter-category')
    await expect(actorPage.getByTestId('advanced-filters')).toBeVisible()
    await expect(categoryFilter).toContainText('innovation')
    await categoryFilter.hover()
    await categoryFilter.locator('.ant-select-clear').click()

    await actorPage.getByRole('searchbox', { name: '关键词' }).fill('Seeded University')
    await actorPage.locator('form[aria-label="赛事筛选"] button[type="submit"]').click()

    await expect(actorPage).toHaveURL('/competitions?keyword=Seeded+University')
    await expect(
      actorPage.getByRole('heading', {
        name: 'Seeded University Innovation Challenge 2025',
      }),
    ).toBeVisible()
  })
})
