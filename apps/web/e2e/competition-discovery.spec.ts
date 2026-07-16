import { expect, test } from './fixtures/actors'

test.use({ actorName: 'student', allowOutboundTrackingConsoleError: true })

function deferred() {
  let release!: () => void
  const promise = new Promise<void>((resolve) => {
    release = resolve
  })
  return { promise, release }
}

test('shows actionable discovery, staged detail, historical context, and direct official links', async ({
  actorPage,
}) => {
  await actorPage.goto('/competitions?registration_status=open&sort=actionable')

  const publicCard = actorPage
    .getByRole('article')
    .filter({ has: actorPage.getByRole('heading', { name: 'Seeded University Innovation Challenge 2025' }) })
  await expect(publicCard).toBeVisible()
  await expect(publicCard).toContainText('报名开放')

  await publicCard.getByRole('link', { name: '查看详情' }).click()
  await expect(
    actorPage.getByRole('heading', { name: 'Seeded University Innovation Challenge 2025' }),
  ).toBeVisible()
  await expect(actorPage.getByText('当前公开修订 r1')).toBeVisible()
  await expect(actorPage.getByRole('heading', { name: 'Registration' })).toBeVisible()
  await expect(actorPage.getByText('报名开始')).toBeVisible()
  await expect(actorPage.getByText('报名截止', { exact: true })).toBeVisible()

  await actorPage.route('**/api/v1/competitions/2001/outbound_clicks', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
  })
  const outboundRequest = actorPage.waitForRequest(
    (request) =>
      request.method() === 'POST' &&
      new URL(request.url()).pathname === '/api/v1/competitions/2001/outbound_clicks',
  )
  const popup = actorPage.waitForEvent('popup')
  await actorPage.getByTestId('official-link').click()
  const request = await outboundRequest
  expect(request.postDataJSON()).toEqual({
    target_type: 'official_url',
    source_surface: 'competition_detail',
  })
  await (await popup).close()

  await actorPage.goto('/competitions/2004')
  await expect(actorPage.getByText('已归档赛事仍保留历史详情')).toBeVisible()
  await expect(
    actorPage.getByText('维护原因：Official archive notice retained for student reference.', {
      exact: false,
    }),
  ).toBeVisible()
  await expect(actorPage.getByText('该赛事已不在默认发现列表中')).toBeVisible()
  await expect(actorPage.getByText(/维护时间：.*2026.*7.*10.*16:00/)).toBeVisible()
  await expect(actorPage.getByTestId('subscription-action')).toHaveCount(0)
  await expect(actorPage.getByTestId('subscription-cancel')).toBeVisible()
})

test.describe('discovery state evidence', () => {
  test.use({ allowDiscoveryRequestErrors: true })

  test('shows list loading and empty states', async ({ actorPage }) => {
    const pending = deferred()
    await actorPage.route('**/api/v1/competitions?*', async (route) => {
      await pending.promise
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: { items: [], pagination: { page: 1, page_size: 20, total: 0 } },
          error: null,
        }),
      })
    })

    await actorPage.goto('/competitions')
    await expect(actorPage.getByRole('status')).toContainText('正在加载赛事')
    pending.release()
    await expect(actorPage.getByText('没有匹配的已发布赛事')).toBeVisible()
  })

  test('shows list error state', async ({ actorPage }) => {
    await actorPage.route('**/api/v1/competitions?*', async (route) => {
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' })
    })

    await actorPage.goto('/competitions')
    await expect(actorPage.getByRole('alert')).toContainText('赛事列表加载失败')
  })

  test('shows detail loading and error states', async ({ actorPage }) => {
    const pending = deferred()
    await actorPage.route('**/api/v1/competitions/2001', async (route) => {
      await pending.promise
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' })
    })

    await actorPage.goto('/competitions/2001')
    await expect(actorPage.getByRole('status')).toContainText('正在加载赛事详情')
    pending.release()
    await expect(actorPage.getByRole('alert')).toContainText('赛事详情加载失败')
  })
})
