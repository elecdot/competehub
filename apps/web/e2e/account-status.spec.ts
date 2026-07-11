import { expect, pendingActor, test } from './fixtures/actors'

test('logs in through the account page and shows a real cookie session', async ({ page }) => {
  await page.goto('/me')

  await page.locator('input[autocomplete="username"]').fill('student.day1@example.edu')
  await page.locator('input[autocomplete="current-password"]').fill('violet harbor lantern orbit 47')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page.getByRole('heading', { name: '当前用户' })).toBeVisible()
  await expect(page.getByText('Day 1 Student')).toBeVisible()
  await expect(page.getByTestId('profile-status')).toContainText('incomplete')
})

test.describe('pending-verification actor', () => {
  test.use({ allowLoginUnauthorizedConsoleError: true })

  test('keeps pending-verification users out of the browser session', async ({ page }) => {
    await page.goto('/me')

    await page.locator('input[autocomplete="username"]').fill(pendingActor.email)
    await page.locator('input[autocomplete="current-password"]').fill(pendingActor.password)
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page.getByTestId('login-error')).toContainText('登录失败')
    await expect(page.getByRole('heading', { name: '当前用户' })).toHaveCount(0)
  })
})

test.describe('profile-incomplete actor', () => {
  test.use({ actorName: 'student' })

  test('updates an incomplete profile to ready and preserves it after reload', async ({
    actorPage,
  }) => {
    await actorPage.goto('/me')
    const profileSection = actorPage.locator('section[aria-labelledby="profile-heading"]')

    await expect(actorPage.getByTestId('profile-status')).toContainText('incomplete')
    await expect(profileSection.getByLabel('学院')).toBeVisible()
    await expect(actorPage.getByTestId('profile-save')).toBeVisible()

    await profileSelect(profileSection, '学院').click()
    await visibleProfileOption(actorPage, '计算机学院').click()
    await profileSelect(profileSection, '专业').click()
    await visibleProfileOption(actorPage, '软件工程').click()
    await profileSelect(profileSection, '年级').click()
    await visibleProfileOption(actorPage, '大二').click()
    await profileSelect(profileSection, '兴趣标签').click()
    await visibleProfileOption(actorPage, '人工智能').click()
    await actorPage.getByTestId('profile-save').click()

    await expect(actorPage.getByTestId('profile-status')).toContainText('recommendation_ready')
    await actorPage.getByRole('button', { name: '刷新' }).click()
    await expect(actorPage.getByTestId('profile-status')).toContainText('recommendation_ready')
    await expect(profileSelect(profileSection, '学院')).toContainText('计算机学院')
  })
})

test.describe('profile-ready actor', () => {
  test.use({ actorName: 'profileReady' })

  test('shows recommendation-ready profile state', async ({ actorPage }) => {
    await actorPage.goto('/me')
    const profileSection = actorPage.locator('section[aria-labelledby="profile-heading"]')

    await expect(actorPage.getByTestId('profile-status')).toContainText('recommendation_ready')
    await expect(profileSection.getByText('缺少字段')).toBeVisible()
    await expect(profileSection.getByText('[]')).toBeVisible()
  })
})

test.describe('profile save failure', () => {
  test.use({ actorName: 'profileReady', allowProfileValidationConsoleError: true })

  test('keeps the editable form and submitted values after a failed save', async ({
    actorPage,
  }) => {
    await actorPage.route('**/api/v1/me/profile', async (route) => {
      if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            data: null,
            error: { code: 'validation_error', message: 'invalid profile' },
          }),
        })
        return
      }
      await route.continue()
    })
    await actorPage.goto('/me')
    const profileSection = actorPage.locator('section[aria-labelledby="profile-heading"]')

    await profileSelect(profileSection, '年级').click()
    await visibleProfileOption(actorPage, '大一').click()
    await actorPage.getByTestId('profile-save').click()

    await expect(actorPage.getByTestId('profile-save-error')).toBeVisible()
    await expect(actorPage.getByTestId('profile-save')).toBeVisible()
    await expect(profileSelect(profileSection, '年级')).toContainText('大一')
  })
})

function profileSelect(profileSection: import('@playwright/test').Locator, label: string) {
  return profileSection
    .locator('.ant-form-item')
    .filter({ hasText: label })
    .locator('.ant-select-selector')
}

function visibleProfileOption(page: import('@playwright/test').Page, title: string) {
  return page.locator('.ant-select-dropdown:visible').getByTitle(title, { exact: true })
}
