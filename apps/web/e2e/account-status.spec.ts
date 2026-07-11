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

test('keeps pending-verification users out of the browser session', async ({ page }) => {
  await page.goto('/me')

  await page.locator('input[autocomplete="username"]').fill(pendingActor.email)
  await page.locator('input[autocomplete="current-password"]').fill(pendingActor.password)
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page.getByTestId('login-error')).toContainText('登录失败')
  await expect(page.getByRole('heading', { name: '当前用户' })).toHaveCount(0)
})

test.describe('profile-incomplete actor', () => {
  test.use({ actorName: 'student' })

  test('shows incomplete profile state and controlled profile options', async ({ actorPage }) => {
    await actorPage.goto('/me')

    await expect(actorPage.getByTestId('profile-status')).toContainText('incomplete')
    await expect(actorPage.getByText('学院')).toBeVisible()
    await expect(actorPage.getByTestId('profile-save')).toBeVisible()

    await actorPage.locator('.profile-form .ant-select-selector').first().click()
    await expect(actorPage.getByTitle('计算机学院')).toBeVisible()
  })
})

test.describe('profile-ready actor', () => {
  test.use({ actorName: 'profileReady' })

  test('shows recommendation-ready profile state', async ({ actorPage }) => {
    await actorPage.goto('/me')

    await expect(actorPage.getByTestId('profile-status')).toContainText('recommendation_ready')
    await expect(actorPage.getByText('缺少字段')).toBeVisible()
    await expect(actorPage.getByText('[]')).toBeVisible()
  })
})
