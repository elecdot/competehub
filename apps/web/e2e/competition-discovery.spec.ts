import { expect, test } from './fixtures/actors'

test.use({ actorName: 'student', allowOutboundTrackingConsoleError: true })

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
})
