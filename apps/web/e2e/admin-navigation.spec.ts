import type { Page } from '@playwright/test'

import { expect, test } from './fixtures/actors'

test('does not expose administrator navigation while an anonymous session resolves', async ({
  page,
}) => {
  let markCurrentUserRequestStarted = () => {}
  let releaseCurrentUserRequest = () => {}
  const currentUserRequestStarted = new Promise<void>((resolve) => {
    markCurrentUserRequestStarted = resolve
  })
  const currentUserRequestBlocked = new Promise<void>((resolve) => {
    releaseCurrentUserRequest = resolve
  })

  await page.route('**/api/v1/me', async (route) => {
    markCurrentUserRequestStarted()
    await currentUserRequestBlocked
    await route.continue()
  })

  const currentUserResponse = page.waitForResponse('**/api/v1/me')
  await page.goto('/competitions')
  await currentUserRequestStarted

  try {
    await expect(page.locator('.app-shell')).toBeVisible()
    await expect(page.getByRole('link', { name: 'CompeteHub' })).toBeVisible()
    await expect(page.getByRole('link', { name: '后台' })).toHaveCount(0)
  } finally {
    releaseCurrentUserRequest()
  }

  await currentUserResponse
  await expect(page.getByRole('link', { name: '后台' })).toHaveCount(0)
})

test('redirects an anonymous direct administrator URL without protected content flash', async ({
  page,
}) => {
  await observeAdministratorContent(page)

  await page.goto('/admin/recommendation-rule-sets')

  await expect(page).toHaveURL(/\/competitions$/)
  await expect(page.getByRole('link', { name: '后台' })).toHaveCount(0)
  expect(await administratorContentWasObserved(page)).toBe(false)
})

test.describe('student session', () => {
  test.use({ actorName: 'student' })

  test('omits administrator navigation and redirects direct administrator URLs', async ({
    actorPage,
  }) => {
    await observeAdministratorContent(actorPage)

    await actorPage.goto('/competitions')
    await expect(actorPage.getByRole('link', { name: '后台' })).toHaveCount(0)

    await actorPage.goto('/admin')
    await expect(actorPage).toHaveURL(/\/competitions$/)
    await expect(actorPage.getByRole('link', { name: '后台' })).toHaveCount(0)
    expect(await administratorContentWasObserved(actorPage)).toBe(false)
  })
})

test.describe('authorized administrator session', () => {
  test.use({ actorName: 'editor' })

  test('shows administrator navigation and preserves direct workspace access', async ({
    actorPage,
  }) => {
    await actorPage.goto('/competitions')
    await expect(actorPage.getByRole('link', { name: '后台' })).toBeVisible()

    await actorPage.goto('/admin')
    await expect(actorPage).toHaveURL(/\/admin$/)
    await expect(
      actorPage.getByRole('heading', { name: '赛事发布工作台' }),
    ).toBeVisible()
  })

  test('fails closed when the initialized administrator session is replaced', async ({
    actorPage,
  }) => {
    await observeAdministratorContent(actorPage)
    await actorPage.goto('/competitions')

    const administratorLink = actorPage.getByRole('link', { name: '后台' })
    await expect(administratorLink).toBeVisible()

    const replacementLogin = await actorPage.request.post('/api/v1/auth/login', {
      data: {
        identity_type: 'email',
        identifier: 'student.day1@example.edu',
        password: 'violet harbor lantern orbit 47',
      },
    })
    expect(replacementLogin).toBeOK()

    const currentUserProbe = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'GET' &&
        new URL(response.url()).pathname === '/api/v1/me' &&
        response.status() === 200,
    )
    await administratorLink.click()
    const currentUserResponse = await currentUserProbe
    const currentUserPayload = (await currentUserResponse.json()) as {
      data: { role: string }
    }
    expect(currentUserPayload.data.role).toBe('student')

    await expect(actorPage).toHaveURL(/\/competitions$/)
    await expect(actorPage.getByRole('link', { name: '后台' })).toHaveCount(0)
    expect(await administratorContentWasObserved(actorPage)).toBe(false)
  })

  test('requires a fresh probe when an older administrator probe is in flight', async ({
    actorPage,
  }) => {
    await observeAdministratorContent(actorPage)
    await actorPage.goto('/competitions')

    const administratorLink = actorPage.getByRole('link', { name: '后台' })
    await expect(administratorLink).toBeVisible()

    let currentUserRequests = 0
    let delayNextCurrentUserRequest = true
    let markStaleRequestStarted = () => {}
    let releaseStaleResponse = () => {}
    const staleRequestStarted = new Promise<void>((resolve) => {
      markStaleRequestStarted = resolve
    })
    const staleResponseBlocked = new Promise<void>((resolve) => {
      releaseStaleResponse = resolve
    })

    await actorPage.route('**/api/v1/me', async (route) => {
      currentUserRequests += 1
      if (!delayNextCurrentUserRequest) {
        await route.continue()
        return
      }

      delayNextCurrentUserRequest = false
      const staleAdministratorResponse = await route.fetch()
      markStaleRequestStarted()
      await staleResponseBlocked
      await route.fulfill({ response: staleAdministratorResponse })
    })

    await actorPage.getByRole('link', { name: '查看详情' }).first().click()
    await staleRequestStarted

    const replacementLogin = await actorPage.request.post('/api/v1/auth/login', {
      data: {
        identity_type: 'email',
        identifier: 'student.day1@example.edu',
        password: 'violet harbor lantern orbit 47',
      },
    })
    expect(replacementLogin).toBeOK()

    // Dispatch synchronously so the guard joins the blocked probe before it is released.
    await administratorLink.evaluate((link) => (link as HTMLElement).click())
    releaseStaleResponse()

    await expect(actorPage).toHaveURL(/\/competitions$/)
    await expect(actorPage.getByRole('link', { name: '后台' })).toHaveCount(0)
    expect(currentUserRequests).toBe(2)
    expect(await administratorContentWasObserved(actorPage)).toBe(false)
  })
})

async function observeAdministratorContent(page: Page) {
  await page.addInitScript(() => {
    const state = { observed: false }
    Object.defineProperty(window, '__administratorContentObserved', {
      get: () => state.observed,
    })

    const observer = new MutationObserver(() => {
      const content = document.body?.textContent ?? ''
      if (content.includes('赛事发布工作台') || content.includes('推荐规则治理')) {
        state.observed = true
      }
    })
    observer.observe(document, { childList: true, subtree: true })
  })
}

async function administratorContentWasObserved(page: Page) {
  return page.evaluate(
    () =>
      (
        window as typeof window & {
          __administratorContentObserved?: boolean
        }
      ).__administratorContentObserved ?? false,
  )
}
