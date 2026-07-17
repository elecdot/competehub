import type { Page } from '@playwright/test'
import { expect, pendingActor, test } from './fixtures/actors'

async function allowPublicEmailRegistration(page: Page) {
  await page.route('**/api/v1/auth/capabilities', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: { public_email_registration_enabled: true },
        error: null,
      }),
    })
  })
}

test('logs in through the login page and shows a real cookie session', async ({ page }) => {
  await allowPublicEmailRegistration(page)
  await page.goto('/login?return_to=/me')

  const accountNav = page.getByRole('navigation', { name: '用户导航' })
  await expect(accountNav.getByRole('link', { name: '登录' })).toBeVisible()
  await expect(accountNav.getByRole('link', { name: '注册' })).toBeVisible()
  await expect(accountNav.getByRole('link', { name: '个人信息' })).toHaveCount(0)
  await expect(page.locator('input[autocomplete="username"]')).toBeVisible()
  await page.locator('input[autocomplete="username"]').fill('student.day1@example.edu')
  const passwordInput = page.locator('input[autocomplete="current-password"]')
  await passwordInput.fill('violet harbor lantern orbit 47')
  await expect(passwordInput).toHaveAttribute('type', 'password')
  await page.locator('.ant-input-password-icon').click()
  await expect(passwordInput).toHaveAttribute('type', 'text')
  await page.locator('.ant-input-password-icon').click()
  await expect(passwordInput).toHaveAttribute('type', 'password')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page).toHaveURL(/\/me$/)
  await expect(accountNav.getByRole('link', { name: '当前用户' })).toContainText('Day 1 Student')
  await expect(accountNav.getByRole('link', { name: '个人信息' })).toBeVisible()
  await expect(accountNav.getByRole('link', { name: '登录' })).toHaveCount(0)
  await expect(accountNav.getByRole('link', { name: '注册' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '个人信息' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Day 1 Student' })).toBeVisible()
  await expect(page.getByTestId('profile-status')).toContainText('资料待完善')
})

test('returns to a safe site-relative path after login', async ({ page }) => {
  await page.goto('/login?return_to=/competitions/123')

  await loginAsDayOneStudent(page)

  await expect(page).toHaveURL(/\/competitions\/123$/)
})

test('falls back to personal information after login without a return target', async ({ page }) => {
  await page.goto('/login')

  await loginAsDayOneStudent(page)

  await expect(page).toHaveURL(/\/me$/)
})

test.describe('unsafe login return targets', () => {
  for (const target of [
    'https://example.com',
    'http://example.com/path',
    '//example.com/path',
    '\\competitions\\123',
    '%2F%2Fexample.com%2Fpath',
    '',
    '%',
  ]) {
    test(`falls back to personal information for ${JSON.stringify(target)}`, async ({ page }) => {
      await page.goto(`/login?return_to=${target}`)

      await loginAsDayOneStudent(page)

      await expect(page).toHaveURL(/\/me$/)
    })
  }
})

test.describe('typed login identities', () => {
  for (const [label, identityType, identifier] of [
    ['邮箱', 'email', 'student.day1@example.edu'],
    ['学号', 'student_no', '20260001'],
    ['手机号', 'phone', '+8613800000000'],
  ] as const) {
    test(`submits ${label} identity type`, async ({ page }) => {
      await page.route('**/api/v1/me/messages/unread_count', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: { unread_count: 0 },
            error: null,
          }),
        })
      })
      await page.route('**/api/v1/auth/login', async (route) => {
        expect(route.request().postDataJSON()).toMatchObject({
          identity_type: identityType,
          identifier,
          password: 'violet harbor lantern orbit 47',
        })
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            data: {
              id: 1,
              display_name: 'Day 1 Student',
              role: 'student',
              capabilities: [],
            },
            error: null,
          }),
        })
      })

      await page.goto('/login')
      if (identityType !== 'email') {
        await page.getByTestId('identity-type').locator('.ant-select-selector').click()
        await page.locator('.ant-select-dropdown:visible').getByTitle(label).click()
      }
      await page.locator('input[autocomplete="username"]').fill(identifier)
      await page.locator('input[autocomplete="current-password"]').fill('violet harbor lantern orbit 47')
      await page.getByRole('button', { name: '登录' }).click()

      await expect(page).toHaveURL(/\/me$/)
    })
  }
})

test.describe('pending-verification actor', () => {
  test.use({ allowLoginUnauthorizedConsoleError: true })

  test('keeps pending-verification users out of the browser session', async ({ page }) => {
    await page.goto('/login')

    await page.locator('input[autocomplete="username"]').fill(pendingActor.email)
    await page.locator('input[autocomplete="current-password"]').fill(pendingActor.password)
    await page.getByRole('button', { name: '登录' }).click()

    await expect(page.getByTestId('login-error')).toContainText('登录失败')
    await expect(page.getByRole('heading', { name: '个人信息' })).toHaveCount(0)
  })
})

test.describe('profile-incomplete actor', () => {
  test.use({ actorName: 'student' })

  test('updates an incomplete profile to ready and preserves it after reload', async ({
    actorPage,
  }) => {
    await actorPage.goto('/me')
    const profileSection = actorPage.locator('section[aria-labelledby="profile-heading"]')

    await expect(actorPage.getByTestId('profile-status')).toContainText('资料待完善')
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
    await actorPage.getByTestId('competition-experience').fill('参加过校级程序设计竞赛')
    await profileSelect(profileSection, '目标偏好').click()
    await visibleProfileOption(actorPage, '提升技术能力').click()
    await actorPage.getByTestId('profile-save').click()

    await expect(actorPage.getByTestId('profile-save-success')).toContainText('画像已保存')
    await expect(actorPage.getByTestId('profile-status')).toContainText('推荐资料已完善')
    await actorPage.getByRole('button', { name: '刷新' }).click()
    await expect(actorPage.getByTestId('profile-status')).toContainText('推荐资料已完善')
    await expect(profileSelect(profileSection, '学院')).toContainText('计算机学院')
    await expect(profileSelect(profileSection, '目标偏好')).toContainText('提升技术能力')
  })
})

test.describe('logout', () => {
  test.use({ actorName: 'profileReady' })

  test('keeps the browser on /me after logout', async ({ actorPage }) => {
    await actorPage.goto('/me')

    await actorPage.getByTestId('logout-button').click()

    await expect(actorPage).toHaveURL(/\/me$/)
    await expect(actorPage.getByText('请先登录')).toBeVisible()
    await expect(actorPage.getByRole('link', { name: '去登录' })).toBeVisible()
    await expect(actorPage.getByRole('heading', { name: '学生画像' })).toHaveCount(0)
  })
})

test('registers with email and verifies without auto-login', async ({ page }) => {
  await allowPublicEmailRegistration(page)
  await page.route('**/api/v1/auth/register', async (route) => {
    await route.fulfill({
      status: 202,
      contentType: 'application/json',
      body: JSON.stringify({ data: { accepted: true }, error: null }),
    })
  })
  await page.route('**/api/v1/auth/verify', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: { verified: true }, error: null }),
    })
  })

  await page.goto('/login')
  await expect(page.getByRole('link', { name: '去注册' })).toBeVisible()
  await page.getByRole('navigation', { name: '用户导航' }).getByRole('link', { name: '注册' }).click()

  await expect(page).toHaveURL(/\/register$/)
  await page.locator('input[autocomplete="email"]').fill('new.student@example.edu')
  await page.locator('input[autocomplete="name"]').fill('New Student')
  await page.locator('input[autocomplete="new-password"]').fill('correct horse campus lantern')
  await page.getByRole('button', { name: '提交注册' }).click()

  await expect(page.getByTestId('register-info')).toContainText(
    '请查看 new.student@example.edu 的验证码邮件',
  )
  await expect(page.getByTestId('register-info')).toContainText(
    '如果之前已经提交过注册，请使用之前收到的验证码，或稍后点击重新发送验证码。',
  )
  await expect(page.getByTestId('resend-code')).toContainText(/秒后可重发/)
  await page.locator('input[autocomplete="one-time-code"]').fill('123456')
  await page.getByTestId('verify-form').getByRole('button', { name: '完成激活' }).click()

  await expect(page.getByTestId('register-complete')).toContainText('注册已完成')
  await expect(page.getByTestId('register-complete').getByRole('link', { name: '去登录' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '个人信息' })).toHaveCount(0)
})

test.describe('registration availability', () => {
  test('hides registration when public email registration is unavailable', async ({ page }) => {
    await page.route('**/api/v1/auth/capabilities', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { public_email_registration_enabled: false },
          error: null,
        }),
      })
    })

    await page.goto('/login')
    await expect(page.getByRole('navigation', { name: '用户导航' }).getByRole('link', { name: '注册' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: '去注册' })).toHaveCount(0)

    await page.goto('/register')
    await expect(page.getByTestId('register-unavailable')).toContainText('当前暂未开放自助注册')
    await expect(page.getByTestId('register-form')).toHaveCount(0)
  })
})

test.describe('profile-ready actor', () => {
  test.use({ actorName: 'profileReady' })

  test('shows recommendation-ready profile state', async ({ actorPage }) => {
    await actorPage.goto('/me')
    const profileSection = actorPage.locator('section[aria-labelledby="profile-heading"]')

    await expect(actorPage.getByTestId('profile-status')).toContainText('推荐资料已完善')
    await expect(profileSection.getByText(/^缺少/)).toHaveCount(0)

    const interestSelect = profileSelect(profileSection, '兴趣标签')
    const interestTagRemoveButtons = interestSelect.locator('.ant-select-selection-item-remove')
    while ((await interestTagRemoveButtons.count()) > 0) {
      await interestTagRemoveButtons.first().click()
    }

    await expect(actorPage.getByTestId('profile-status')).toContainText('资料待完善')
    await expect(profileSection.getByText('缺少兴趣标签')).toBeVisible()
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

async function loginAsDayOneStudent(page: import('@playwright/test').Page) {
  await page.locator('input[autocomplete="username"]').fill('student.day1@example.edu')
  await page.locator('input[autocomplete="current-password"]').fill('violet harbor lantern orbit 47')
  await page.getByRole('button', { name: '登录' }).click()
}
