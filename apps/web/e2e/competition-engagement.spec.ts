import { expect, test } from './fixtures/actors'
import type { SubscriptionNodeType } from '../src/types/competition'

interface ReminderSettings {
  message_enabled: boolean
  default_remind_days: number
  default_reminder_node_types: SubscriptionNodeType[]
}

test.describe('competition engagement', () => {
  test.use({ actorName: 'student' })
  let originalStudentReminderSettings: ReminderSettings | null = null

  test.beforeEach(async ({ actorPage }) => {
    const competition = await firstPublicCompetition(actorPage)
    await actorPage.request.delete(`/api/v1/competitions/${competition.id}/favorite`)
    await actorPage.request.delete(`/api/v1/competitions/${competition.id}/subscription`)
  })

  test.afterEach(async ({ actorPage }) => {
    if (originalStudentReminderSettings !== null) {
      await updateReminderSettings(actorPage, originalStudentReminderSettings)
      originalStudentReminderSettings = null
    }
  })

  test('favorites and unfavorites a competition from the canonical response state', async ({
    actorPage,
  }) => {
    const competition = await firstPublicCompetition(actorPage)
    let favoriteRequests = 0
    await actorPage.route(`**/api/v1/competitions/${competition.id}/favorite`, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.continue()
        return
      }
      favoriteRequests += 1
      const response = await route.fetch()
      await new Promise((resolve) => setTimeout(resolve, 100))
      await route.fulfill({ response })
    })
    await actorPage.goto(`/competitions/${competition.id}`)

    const favoriteButton = actorPage.getByTestId('favorite-action')
    await expect(favoriteButton).toHaveAttribute('aria-pressed', 'false')

    const favoriteResponse = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response.url().endsWith(`/api/v1/competitions/${competition.id}/favorite`),
    )
    await favoriteButton.click()
    await expect(favoriteButton).toBeDisabled()
    expect(favoriteRequests).toBe(1)
    expect((await favoriteResponse).ok()).toBeTruthy()
    await expect(favoriteButton).toHaveAttribute('aria-pressed', 'true')

    const unfavoriteResponse = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'DELETE' &&
        response.url().endsWith(`/api/v1/competitions/${competition.id}/favorite`),
    )
    await favoriteButton.click()
    expect((await unfavoriteResponse).ok()).toBeTruthy()
    await expect(favoriteButton).toHaveAttribute('aria-pressed', 'false')
  })

  test('restores persisted consent after reloading detail without submitting a mutation', async ({
    actorPage,
  }) => {
    const competition = await firstPublicCompetition(actorPage)
    const persistedNodeTypes = competition.nodeTypes.slice(0, 1)
    originalStudentReminderSettings = await fetchReminderSettings(actorPage)
    await updateReminderSettings(actorPage, {
      message_enabled: true,
      default_remind_days: 2,
      default_reminder_node_types: competition.nodeTypes,
    })
    const created = await actorPage.request.post(`/api/v1/competitions/${competition.id}/subscription`, {
      data: {
        reminder_enabled: false,
        remind_days: 8,
        node_types: persistedNodeTypes,
      },
    })
    expect([200, 201]).toContain(created.status())

    let subscriptionMutations = 0
    await actorPage.route(`**/api/v1/competitions/${competition.id}/subscription`, async (route) => {
      if (route.request().method() === 'POST' || route.request().method() === 'PATCH') {
        subscriptionMutations += 1
      }
      await route.continue()
    })
    await actorPage.goto(`/competitions/${competition.id}`)
    await actorPage.reload()
    await actorPage.getByTestId('subscription-action').click()
    const consent = actorPage.getByTestId('subscription-consent')

    await expect(consent.getByLabel('启用提醒')).not.toBeChecked()
    await expect(consent.getByLabel('提前天数')).toHaveValue('8')
    for (const nodeType of competition.nodeTypes) {
      const node = consent.getByLabel(subscriptionNodeLabels[nodeType])
      if (persistedNodeTypes.includes(nodeType)) {
        await expect(node).toBeChecked()
      } else {
        await expect(node).not.toBeChecked()
      }
    }
    expect(subscriptionMutations).toBe(0)
  })

  test('creates, updates, cancels, and re-subscribes with complete consent', async ({ actorPage }) => {
    const competition = await firstPublicCompetition(actorPage)
    await actorPage.goto(`/competitions/${competition.id}`)

    await actorPage.getByTestId('subscription-action').click()
    const consent = actorPage.getByTestId('subscription-consent')
    await expect(consent).toBeVisible()
    await consent.getByLabel('启用提醒').uncheck()
    await consent.getByLabel('提前天数').fill('2')
    await selectSubscriptionNodeTypes(consent, competition.nodeTypes)

    const createResponse = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response.url().endsWith(`/api/v1/competitions/${competition.id}/subscription`),
    )
    await consent.getByRole('button', { name: '确认订阅' }).click()
    const createRequest = await createResponse
    expect(createRequest.request().postDataJSON()).toEqual({
      reminder_enabled: false,
      remind_days: 2,
      node_types: competition.nodeTypes,
    })
    expect(createRequest.ok()).toBeTruthy()
    await expect(actorPage.getByTestId('subscription-summary')).toContainText('已订阅')

    await actorPage.getByTestId('subscription-action').click()
    await consent.getByLabel('启用提醒').check()
    await consent.getByLabel('提前天数').fill('5')
    const updateResponse = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'PATCH' &&
        response.url().endsWith(`/api/v1/competitions/${competition.id}/subscription`),
    )
    await consent.getByRole('button', { name: '保存订阅设置' }).click()
    const updateRequest = await updateResponse
    expect(updateRequest.request().postDataJSON()).toEqual({
      reminder_enabled: true,
      remind_days: 5,
      node_types: competition.nodeTypes,
    })
    expect(updateRequest.ok()).toBeTruthy()
    await expect(actorPage.getByTestId('subscription-summary')).toContainText('提前 5 天')

    const cancelResponse = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'DELETE' &&
        response.url().endsWith(`/api/v1/competitions/${competition.id}/subscription`),
    )
    await actorPage.getByTestId('subscription-cancel').click()
    expect((await cancelResponse).ok()).toBeTruthy()
    await expect(actorPage.getByTestId('subscription-summary')).toContainText('未订阅')

    let resubscriptionMutations = 0
    await actorPage.route(`**/api/v1/competitions/${competition.id}/subscription`, async (route) => {
      if (route.request().method() === 'POST') {
        resubscriptionMutations += 1
      }
      await route.continue()
    })
    await actorPage.getByTestId('subscription-action').click()
    await expect(consent.getByLabel('启用提醒')).toBeChecked()
    await expect(consent.getByLabel('提前天数')).toHaveValue('5')
    for (const nodeType of competition.nodeTypes) {
      await expect(consent.getByLabel(subscriptionNodeLabels[nodeType])).toBeChecked()
    }
    expect(resubscriptionMutations).toBe(0)
    await selectSubscriptionNodeTypes(consent, competition.nodeTypes)
    const resubscribeResponse = actorPage.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response.url().endsWith(`/api/v1/competitions/${competition.id}/subscription`),
    )
    await consent.getByRole('button', { name: '确认订阅' }).click()
    expect((await resubscribeResponse).ok()).toBeTruthy()
    expect(resubscriptionMutations).toBe(1)
    await expect(actorPage.getByTestId('subscription-summary')).toContainText('已订阅')
  })
})

test.describe('first subscription consent', () => {
  test.use({ actorName: 'profileReady' })
  let originalProfileReadyReminderSettings: ReminderSettings | null = null

  test.afterEach(async ({ actorPage }) => {
    if (originalProfileReadyReminderSettings !== null) {
      await updateReminderSettings(actorPage, originalProfileReadyReminderSettings)
      originalProfileReadyReminderSettings = null
    }
  })

  test('prefills first subscription consent from authoritative reminder settings without mutation', async ({
    actorPage,
  }) => {
    const competition = await firstPublicCompetition(actorPage)
    const defaultNodeTypes = competition.nodeTypes.slice(0, 1)
    originalProfileReadyReminderSettings = await fetchReminderSettings(actorPage)
    await updateReminderSettings(actorPage, {
      message_enabled: false,
      default_remind_days: 8,
      default_reminder_node_types: defaultNodeTypes,
    })
    let subscriptionMutations = 0
    await actorPage.route(`**/api/v1/competitions/${competition.id}/subscription`, async (route) => {
      if (route.request().method() === 'POST' || route.request().method() === 'PATCH') {
        subscriptionMutations += 1
      }
      await route.continue()
    })

    await actorPage.goto(`/competitions/${competition.id}`)
    await actorPage.getByTestId('subscription-action').click()
    const consent = actorPage.getByTestId('subscription-consent')

    await expect(consent.getByLabel('启用提醒')).not.toBeChecked()
    await expect(consent.getByLabel('提前天数')).toHaveValue('8')
    for (const nodeType of competition.nodeTypes) {
      const node = consent.getByLabel(subscriptionNodeLabels[nodeType])
      if (defaultNodeTypes.includes(nodeType)) {
        await expect(node).toBeChecked()
      } else {
        await expect(node).not.toBeChecked()
      }
    }
    expect(subscriptionMutations).toBe(0)
  })
})

test('anonymous engagement login returns to the competition without replaying an action', async ({ page }) => {
  const competition = await firstPublicCompetition(page)
  await page.request.delete(`/api/v1/competitions/${competition.id}/favorite`)
  await page.goto(`/competitions/${competition.id}`)

  await page.getByTestId('favorite-action').click()
  await expect(page).toHaveURL(
    new RegExp(`/me\\?return_to=/competitions/${competition.id}`),
  )

  await page.locator('input[autocomplete="username"]').fill('student.day1@example.edu')
  await page.locator('input[autocomplete="current-password"]').fill('violet harbor lantern orbit 47')
  await page.getByRole('button', { name: '登录' }).click()

  await expect(page).toHaveURL(new RegExp(`/competitions/${competition.id}$`))
  await expect(page.getByTestId('favorite-action')).toHaveAttribute('aria-pressed', 'false')
})

async function firstPublicCompetition(page: import('@playwright/test').Page) {
  const response = await page.request.get('/api/v1/competitions?page=1&page_size=1')
  expect(response).toBeOK()
  const payload = (await response.json()) as { data: { items: Array<{ id: number }> } }
  const competition = payload.data.items[0]
  expect(competition, 'the e2e seed should include a public competition').toBeDefined()
  if (!competition) throw new Error('the e2e seed should include a public competition')

  const detailResponse = await page.request.get(`/api/v1/competitions/${competition.id}`)
  expect(detailResponse).toBeOK()
  const detail = (await detailResponse.json()) as {
    data: { time_nodes: Array<{ node_type: string; occurs_at: string | null }> }
  }
  const nodeTypes = detail.data.time_nodes
    .filter((node) => node.occurs_at !== null)
    .map((node) => node.node_type)
    .filter(isSubscriptionNodeType)
  expect(nodeTypes, 'the public competition should expose a selectable reminder node').not.toEqual([])
  return { ...competition, nodeTypes }
}

async function selectSubscriptionNodeTypes(
  consent: import('@playwright/test').Locator,
  nodeTypes: SubscriptionNodeType[],
) {
  for (const nodeType of nodeTypes) {
    await consent.getByLabel(subscriptionNodeLabels[nodeType]).check()
  }
}

async function fetchReminderSettings(page: import('@playwright/test').Page): Promise<ReminderSettings> {
  const response = await page.request.get('/api/v1/me/profile')
  expect(response).toBeOK()
  const payload = (await response.json()) as {
    data: ReminderSettings
  }
  return payload.data
}

async function updateReminderSettings(
  page: import('@playwright/test').Page,
  settings: ReminderSettings,
) {
  const response = await page.request.patch('/api/v1/me/preferences', { data: settings })
  expect(response).toBeOK()
}

const subscriptionNodeLabels: Record<SubscriptionNodeType, string> = {
  registration_deadline: '报名截止',
  submission_deadline: '作品提交截止',
  competition_start: '比赛开始',
}

function isSubscriptionNodeType(nodeType: string): nodeType is SubscriptionNodeType {
  return (
    nodeType === 'registration_deadline' ||
    nodeType === 'submission_deadline' ||
    nodeType === 'competition_start'
  )
}
