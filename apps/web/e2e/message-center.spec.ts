import { expect, test } from './fixtures/actors'

interface Deferred {
  promise: Promise<void>
  resolve: () => void
}

interface DelayedUnreadCountResponse {
  unreadCount: number
  started: Deferred
  release: Deferred
  fulfilled: Deferred
}

test.describe.serial('message center journey', () => {
  test.use({ actorName: 'student' })

  test.describe('transient count failure', () => {
    test.use({ allowMessageServiceUnavailableResponse: true })

    test('keeps the confirmed badge and session', async ({ actorPage }) => {
      let failUnreadCount = false
      await actorPage.route('**/api/v1/me/messages/unread_count', async (route) => {
        if (!failUnreadCount) {
          await route.continue()
          return
        }
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({
            data: null,
            error: { code: 'service_unavailable', message: 'Try again later.' },
          }),
        })
      })

      await actorPage.goto('/me/messages')
      const messageLink = actorPage.getByTestId('message-center-link')
      await expect(messageLink).toHaveAttribute('aria-label', '消息，2 条未读')
      await expect(
        actorPage.getByText('Seeded competition is offline', { exact: true }),
      ).toBeVisible()

      failUnreadCount = true
      const failedRefresh = actorPage.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === '/api/v1/me/messages/unread_count' &&
          response.status() === 503,
      )
      await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
      await failedRefresh

      await expect(actorPage).toHaveURL(/\/me\/messages$/)
      await expect(messageLink).toHaveAttribute('aria-label', '消息，2 条未读')
      await expect(messageLink.locator('.ant-badge-count')).toHaveText('2')
      await expect(
        actorPage.getByText('Seeded competition is offline', { exact: true }),
      ).toBeVisible()
    })
  })

  test.describe('expired message session', () => {
    test.use({ allowMessageUnauthorizedResponse: true })

    test('clears stale notifications and redirects on focus', async ({ actorPage }) => {
      const returnTo = '/me/messages?read_status=unread&page_size=2'
      const filteredInitialList = actorPage.waitForResponse((response) => {
        const url = new URL(response.url())
        return (
          url.pathname === '/api/v1/me/messages' &&
          url.searchParams.get('read_status') === 'unread' &&
          url.searchParams.get('page_size') === '2' &&
          response.status() === 200
        )
      })
      await actorPage.goto(returnTo)
      await filteredInitialList

      const staleTitle = actorPage.getByText('Seeded competition is offline', { exact: true })
      await expect(staleTitle).toBeVisible()
      await expect(actorPage.getByTestId('message-center-link')).toHaveAttribute(
        'aria-label',
        '消息，2 条未读',
      )

      let protectedMessageRequests = 0
      actorPage.on('request', (request) => {
        if (new URL(request.url()).pathname.startsWith('/api/v1/me/messages')) {
          protectedMessageRequests += 1
        }
      })

      const logoutResponse = await actorPage.request.post('/api/v1/auth/logout')
      expect(logoutResponse).toBeOK()
      const unauthorizedRefresh = actorPage.waitForResponse(
        (response) =>
          new URL(response.url()).pathname.startsWith('/api/v1/me/messages') &&
          response.status() === 401,
      )
      await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
      await unauthorizedRefresh

      await expect.poll(() => currentLocation(actorPage)).toEqual({
        pathname: '/me',
        search: { return_to: returnTo },
      })
      await expect(staleTitle).toHaveCount(0)
      await expect(actorPage.getByTestId('message-item')).toHaveCount(0)
      await expect(actorPage.getByTestId('message-center-link')).toHaveCount(0)
      await expect(actorPage.locator('.ant-badge-count')).toHaveCount(0)

      const requestsAfterRedirect = protectedMessageRequests
      await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
      await actorPage.waitForTimeout(300)
      expect(protectedMessageRequests).toBe(requestsAfterRedirect)
    })
  })

  test.describe('stale response from a replaced session', () => {
    test.use({ allowMessageUnauthorizedResponse: true })

    test('does not clear the newly authenticated student', async ({ actorPage }) => {
      let delayNextUnreadCount = false
      const staleRequestStarted = deferred()
      const releaseStaleRequest = deferred()
      const staleResponseFulfilled = deferred()

      await actorPage.route('**/api/v1/me/messages/unread_count', async (route) => {
        if (!delayNextUnreadCount) {
          await route.continue()
          return
        }

        delayNextUnreadCount = false
        staleRequestStarted.resolve()
        await releaseStaleRequest.promise
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            data: null,
            error: { code: 'unauthorized', message: 'Session expired.' },
          }),
        })
        staleResponseFulfilled.resolve()
      })

      await actorPage.goto('/competitions')
      await expect(actorPage.getByTestId('message-center-link')).toHaveAttribute(
        'aria-label',
        '消息，2 条未读',
      )

      delayNextUnreadCount = true
      await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
      await staleRequestStarted.promise

      const logoutResponse = await actorPage.request.post('/api/v1/auth/logout')
      expect(logoutResponse).toBeOK()
      await actorPage.getByRole('link', { name: '个人信息', exact: true }).click()
      await actorPage.getByRole('link', { name: '去登录' }).click()
      await expect(actorPage.locator('input[autocomplete="username"]')).toBeVisible()

      await actorPage
        .locator('input[autocomplete="username"]')
        .fill('student.day1@example.edu')
      await actorPage
        .locator('input[autocomplete="current-password"]')
        .fill('violet harbor lantern orbit 47')
      await actorPage.getByRole('button', { name: '登录' }).click()
      await expect(actorPage).toHaveURL(/\/me$/)

      releaseStaleRequest.resolve()
      await staleResponseFulfilled.promise
      await actorPage.waitForTimeout(100)

      await expect(actorPage.getByTestId('message-center-link')).toHaveAttribute(
        'aria-label',
        '消息，2 条未读',
      )
    })

    test('isolates a replacement discovered through the current-user probe', async ({
      actorPage,
    }) => {
      let delayNextUnreadCount = false
      const staleRequestStarted = deferred()
      const releaseStaleRequest = deferred()
      const staleResponseFulfilled = deferred()

      await actorPage.route('**/api/v1/me/messages/unread_count', async (route) => {
        if (!delayNextUnreadCount) {
          await route.continue()
          return
        }

        delayNextUnreadCount = false
        staleRequestStarted.resolve()
        await releaseStaleRequest.promise
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            data: null,
            error: { code: 'unauthorized', message: 'Session expired.' },
          }),
        })
        staleResponseFulfilled.resolve()
      })

      await actorPage.goto('/competitions')
      await expect(actorPage.getByTestId('message-center-link')).toHaveAttribute(
        'aria-label',
        '消息，2 条未读',
      )

      delayNextUnreadCount = true
      await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
      await staleRequestStarted.promise

      const loginResponse = await actorPage.request.post('/api/v1/auth/login', {
        data: {
          identity_type: 'email',
          identifier: 'profile.student-day1@example.edu',
          password: 'green campus theorem delta 64',
        },
      })
      expect(loginResponse).toBeOK()

      const currentUserProbe = actorPage.waitForResponse(
        (response) =>
          response.request().method() === 'GET' &&
          new URL(response.url()).pathname === '/api/v1/me' &&
          response.status() === 200,
      )
      await actorPage.getByRole('link', { name: '个人信息', exact: true }).click()
      const currentUserResponse = await currentUserProbe
      const currentUserPayload = (await currentUserResponse.json()) as {
        data: { id: number }
      }
      expect(currentUserPayload.data.id).toBe(1004)
      await expect(
        actorPage.getByRole('heading', { name: 'Profile Ready Student' }),
      ).toBeVisible()

      releaseStaleRequest.resolve()
      await staleResponseFulfilled.promise

      await expect(
        actorPage.getByRole('heading', { name: 'Profile Ready Student' }),
      ).toBeVisible()
      await expect(actorPage.getByTestId('message-center-link')).toHaveAttribute(
        'aria-label',
        '消息，暂无未读',
      )
    })
  })

  test('keeps the global unread badge and retained message history in sync', async ({
    actorPage,
  }) => {
    let unreadCountRequests = 0
    let finishedUnreadCountRequests = 0
    let delayedUnreadCountResponse: DelayedUnreadCountResponse | null = null

    actorPage.on('requestfinished', (request) => {
      if (new URL(request.url()).pathname === '/api/v1/me/messages/unread_count') {
        finishedUnreadCountRequests += 1
      }
    })

    await actorPage.route('**/api/v1/me/messages/unread_count', async (route) => {
      unreadCountRequests += 1
      const delayedResponse = delayedUnreadCountResponse
      if (!delayedResponse) {
        await route.continue()
        return
      }

      delayedUnreadCountResponse = null
      delayedResponse.started.resolve()
      await delayedResponse.release.promise
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { unread_count: delayedResponse.unreadCount },
          error: null,
        }),
      })
      delayedResponse.fulfilled.resolve()
    })

    const delayNextUnreadCountResponse = (unreadCount: number) => {
      const delayedResponse = {
        unreadCount,
        started: deferred(),
        release: deferred(),
        fulfilled: deferred(),
      }
      delayedUnreadCountResponse = delayedResponse
      return delayedResponse
    }

    await actorPage.goto('/competitions')

    const messageLink = actorPage.getByTestId('message-center-link')
    await expect(messageLink).toBeVisible()
    await expect(messageLink).toHaveAttribute('aria-label', '消息，2 条未读')
    await expect(messageLink.locator('.ant-badge-count')).toHaveText('2')

    expect(unreadCountRequests).toBeGreaterThan(0)

    const beforeOrdinaryRouteChange = unreadCountRequests
    await actorPage.getByRole('link', { name: '推荐', exact: true }).click()
    await expect(actorPage).toHaveURL(/\/recommendations$/)
    await expect.poll(() => unreadCountRequests).toBeGreaterThan(beforeOrdinaryRouteChange)

    const beforeReturnRouteChange = unreadCountRequests
    await actorPage.getByRole('link', { name: '赛事', exact: true }).click()
    await expect(actorPage).toHaveURL(/\/competitions$/)
    await expect.poll(() => unreadCountRequests).toBeGreaterThan(beforeReturnRouteChange)
    await expect.poll(() => finishedUnreadCountRequests).toBe(unreadCountRequests)

    const beforeWindowFocus = unreadCountRequests
    await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
    await expect.poll(() => unreadCountRequests).toBeGreaterThan(beforeWindowFocus)

    const idleBaseline = unreadCountRequests
    await actorPage.waitForTimeout(400)
    expect(unreadCountRequests).toBe(idleBaseline)

    const beforeMessageCenterEntry = unreadCountRequests
    await messageLink.click()
    await expect(actorPage).toHaveURL(/\/me\/messages$/)
    await expect(actorPage.getByRole('heading', { name: '消息中心' })).toBeVisible()
    await expect.poll(() => unreadCountRequests).toBeGreaterThan(beforeMessageCenterEntry)

    const messageItems = actorPage.getByTestId('message-item')
    await expect(messageItems).toHaveCount(3)
    expect(await messageItems.evaluateAll((items) => items.map((item) => item.id))).toEqual([
      'message-3003',
      'message-3002',
      'message-3001',
    ])

    const unavailableMessage = actorPage.getByTestId('message-item-3003')
    await expect(unavailableMessage).toContainText('赛事当前不可访问')
    await expect(unavailableMessage.getByRole('link', { name: '查看赛事' })).toHaveCount(0)
    await expect(
      actorPage.getByTestId('message-item-3002').getByRole('link', { name: '查看赛事' }),
    ).toBeVisible()

    await actorPage.setViewportSize({ width: 390, height: 844 })
    await expect(messageItems).toHaveCount(3)
    await expectNoHorizontalOverflow(actorPage)

    await actorPage.setViewportSize({ width: 480, height: 844 })
    await expect(messageLink).toBeVisible()
    await expect(
      actorPage
        .getByRole('navigation', { name: '用户导航' })
        .getByRole('link', { name: '个人信息', exact: true }),
    ).toBeVisible()
    await expectNoHorizontalOverflow(actorPage)

    await actorPage.setViewportSize({ width: 1280, height: 900 })

    const staleCountAfterRead = delayNextUnreadCountResponse(2)
    await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
    await staleCountAfterRead.started.promise
    await unavailableMessage.getByRole('button', { name: /标为已读/ }).click()
    await expect(messageLink).toHaveAttribute('aria-label', '消息，1 条未读')
    staleCountAfterRead.release.resolve()
    await staleCountAfterRead.fulfilled.promise
    await actorPage.waitForTimeout(100)
    await expect(messageLink).toHaveAttribute('aria-label', '消息，1 条未读')

    await actorPage.goto('/me/messages?page_size=2')
    await expect(messageItems).toHaveCount(2)
    await actorPage
      .getByTestId('message-pagination')
      .locator('.ant-pagination-item-2')
      .click()
    await expect.poll(() => currentSearch(actorPage)).toEqual({ page: '2', page_size: '2' })
    await expect(actorPage.getByTestId('message-item-3001')).toBeVisible()

    await selectMessageType(actorPage, '赛事时间变更')
    await expect.poll(() => currentSearch(actorPage)).toEqual({
      message_type: 'competition_time_changed',
      page_size: '2',
    })
    await expect(messageItems).toHaveCount(1)
    await expect(actorPage.getByTestId('message-item-3002')).toBeVisible()

    await selectMessageType(actorPage, '全部类型')
    await actorPage.getByRole('tab', { name: '未读' }).click()
    await expect.poll(() => currentSearch(actorPage)).toEqual({
      page_size: '2',
      read_status: 'unread',
    })
    await expect(messageItems).toHaveCount(1)

    await actorPage.goto('/me/messages?read_status=unread&page=2&page_size=1')
    const dueMessage = actorPage.getByTestId('message-item-3001')
    await expect(dueMessage).toBeVisible()
    await expect.poll(() => currentSearch(actorPage)).toEqual({
      page_size: '1',
      read_status: 'unread',
    })

    const staleCountAfterReadAll = delayNextUnreadCountResponse(1)
    await actorPage.evaluate(() => window.dispatchEvent(new Event('focus')))
    await staleCountAfterReadAll.started.promise
    await actorPage.getByTestId('mark-all-read').click()
    await expect(actorPage.getByTestId('message-empty')).toBeVisible()
    await expect(messageLink).toHaveAttribute('aria-label', '消息，暂无未读')
    await expect(messageLink.locator('.ant-badge-count')).toBeHidden()
    staleCountAfterReadAll.release.resolve()
    await staleCountAfterReadAll.fulfilled.promise
    await actorPage.waitForTimeout(100)
    await expect(messageLink).toHaveAttribute('aria-label', '消息，暂无未读')
    await expect(messageLink.locator('.ant-badge-count')).toBeHidden()

    await actorPage.reload()
    await expect(actorPage.getByTestId('message-empty')).toBeVisible()
    await expect(messageLink).toHaveAttribute('aria-label', '消息，暂无未读')

    let protectedMessageRequests = 0
    const countProtectedMessageRequests = (request: import('@playwright/test').Request) => {
      if (new URL(request.url()).pathname.startsWith('/api/v1/me/messages')) {
        protectedMessageRequests += 1
      }
    }
    actorPage.on('request', countProtectedMessageRequests)

    const logoutResponse = await actorPage.request.post('/api/v1/auth/logout')
    expect(logoutResponse).toBeOK()
    await actorPage.goto('/me/messages')
    await expect(actorPage).toHaveURL(/\/me\?return_to=\/me\/messages$/)

    const adminLoginResponse = await actorPage.request.post('/api/v1/auth/login', {
      data: {
        identity_type: 'email',
        identifier: 'admin.day1@example.edu',
        password: 'copper meadow signal river 82',
      },
    })
    expect(adminLoginResponse).toBeOK()
    await actorPage.goto('/me/messages')
    await expect(actorPage.getByText('仅学生账号可查看消息')).toBeVisible()
    await expect(actorPage.getByTestId('message-center-link')).toHaveCount(0)
    expect(protectedMessageRequests).toBe(0)
    actorPage.off('request', countProtectedMessageRequests)
  })
})

async function currentSearch(page: import('@playwright/test').Page) {
  return page.evaluate(() => Object.fromEntries(new URL(window.location.href).searchParams))
}

async function currentLocation(page: import('@playwright/test').Page) {
  return page.evaluate(() => {
    const url = new URL(window.location.href)
    return {
      pathname: url.pathname,
      search: Object.fromEntries(url.searchParams),
    }
  })
}

function deferred(): Deferred {
  let resolve = () => undefined
  const promise = new Promise<void>((resolvePromise) => {
    resolve = resolvePromise
  })
  return { promise, resolve }
}

async function expectNoHorizontalOverflow(page: import('@playwright/test').Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      ),
    )
    .toBe(true)
}

async function selectMessageType(page: import('@playwright/test').Page, label: string) {
  await page.getByTestId('message-type-filter').click()
  await page
    .locator('.ant-select-dropdown:visible')
    .getByText(label, { exact: true })
    .click()
}
