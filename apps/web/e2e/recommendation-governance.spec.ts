import type { Page } from '@playwright/test'

import { expect, test } from './fixtures/actors'

test.use({ actorName: 'editor' })

test('editor previews and submits, then a distinct reviewer activates the candidate', async ({
  actorPage,
}) => {
  await actorPage.goto('/admin/recommendation-rule-sets')
  await expect(actorPage.getByRole('heading', { name: '推荐规则治理' })).toBeVisible()
  await expect(actorPage.getByTestId('rule-set-v1')).toContainText('当前生效')

  await actorPage.getByTestId('clone-rule-set').click()
  await expect(actorPage.getByTestId('rule-set-v2')).toContainText('草稿')

  const deadlineWeight = actorPage.getByTestId('rule-weight-deadline_urgency')
  await deadlineWeight.fill('26')
  await actorPage.getByTestId('save-rule-set').click()
  await expect(actorPage.getByText('已保存 v2')).toBeVisible()

  await actorPage.getByTestId('preview-competition-ids').fill('2001')
  const previewResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith('/api/v1/admin/recommendation_rule_sets/2/preview'),
  )
  await actorPage.getByTestId('run-preview').click()
  const previewResponse = await previewResponsePromise
  expect(previewResponse.ok()).toBe(true)
  const previewData = (await previewResponse.json()).data
  expect(previewData).toMatchObject({
    version: 2,
    results: [
      {
        position: 1,
        competition_id: 2001,
        competition: {
          id: 2001,
          title: 'Seeded University Innovation Challenge 2025',
          edition_label: '2025',
        },
      },
    ],
  })
  expect(JSON.stringify(previewData)).not.toMatch(
    /score|probability|percentage|percentile|weight_contribution/i,
  )
  const previewResults = actorPage.getByTestId('preview-results')
  await expect(previewResults).toContainText('v2 / personalized')
  await expect(previewResults).toContainText('#1 Seeded University Innovation Challenge 2025')
  await expect(previewResults).toContainText('major_match')
  await expect(previewResults).toContainText('grade_match')
  await expect(previewResults).toContainText('interest_match')
  await expect(previewResults).not.toContainText(/score|probability|percentage|percentile/i)

  await actorPage.getByTestId('submit-rule-set').click()
  await expect(actorPage.getByTestId('rule-set-v2')).toContainText('待审核')

  const submitterResponse = await actorPage.request.get('/api/v1/me')
  expect(submitterResponse).toBeOK()
  const submitter = (await submitterResponse.json()).data
  expect(submitter.capabilities).toEqual(
    expect.arrayContaining(['recommendation_editor', 'recommendation_reviewer']),
  )

  await expect(actorPage.getByText('提交者不能审核自己的候选版本')).toBeVisible()
  await expect(actorPage.getByTestId('approve-rule-set')).toBeDisabled()

  const selfReview = await actorPage.request.post(
    '/api/v1/admin/recommendation_rule_sets/2/review',
    { data: { action: 'approve', comment: 'Self approval must be forbidden.' } },
  )
  expect(selfReview.status()).toBe(403)
  expect((await selfReview.json()).error.code).toBe('forbidden')

  const pendingHistoryResponse = await actorPage.request.get(
    '/api/v1/admin/recommendation_rule_sets',
  )
  expect(pendingHistoryResponse).toBeOK()
  const pendingCandidate = (await pendingHistoryResponse.json()).data.items.find(
    (item: { rule_set_id: number }) => item.rule_set_id === 2,
  )
  expect(pendingCandidate).toMatchObject({
    status: 'pending_review',
    reviewed_by: null,
    decided_at: null,
    terminal_review_status: null,
  })

  await switchActor(
    actorPage,
    'reviewer.day1@example.edu',
    'silver orchard compass cloud 59',
  )
  await actorPage.reload()
  await actorPage.getByTestId('rule-set-v2').click()
  const evidence = actorPage.getByTestId('governance-evidence')
  await expect(evidence).toContainText('Day 1 Admin')
  await expect(evidence).toContainText('提交时间')
  await expect(evidence).toContainText('基线版本')
  await expect(evidence).toContainText('v1')
  await expect(actorPage.getByText('变更规则').locator('..')).toContainText('deadline_urgency')
  await expect(actorPage.getByText('影响').locator('..')).toContainText('ordering_may_change')

  await actorPage.getByTestId('review-comment').fill('规则差异与 preview 影响均已核验。')
  await actorPage.getByTestId('approve-rule-set').click()
  await expect(actorPage.getByTestId('rule-set-v2')).toContainText('当前生效')
  await expect(actorPage.getByTestId('rule-set-v1')).toContainText('已退役')

  await actorPage.reload()
  await expect(actorPage.getByTestId('rule-set-v2')).toContainText('当前生效')
  await expect(actorPage.getByTestId('rule-set-v1')).toContainText('已退役')
  await actorPage.getByTestId('rule-set-v2').click()
  await expect(actorPage.getByTestId('governance-evidence')).toContainText(
    '规则差异与 preview 影响均已核验。',
  )
})

test.describe('governance access boundaries', () => {
  test.use({ actorName: 'adminNoRecommendation' })

  test('an ordinary admin without recommendation capability is denied', async ({ actorPage }) => {
    const apiResponse = await actorPage.request.get('/api/v1/admin/recommendation_rule_sets')
    expect(apiResponse.status()).toBe(403)
    await actorPage.goto('/admin/recommendation-rule-sets')
    await expect(actorPage.getByText('无权访问推荐规则治理', { exact: true })).toBeVisible()
  })
})

test.describe('student governance access boundary', () => {
  test.use({ actorName: 'student' })

  test('a student is denied by both API and governance page', async ({ actorPage }) => {
    const apiResponse = await actorPage.request.get('/api/v1/admin/recommendation_rule_sets')
    expect(apiResponse.status()).toBe(403)
    await actorPage.goto('/admin/recommendation-rule-sets')
    await expect(actorPage.getByText('无权访问推荐规则治理', { exact: true })).toBeVisible()
  })
})

async function switchActor(page: Page, account: string, password: string) {
  const logoutResponse = await page.request.post('/api/v1/auth/logout')
  expect(logoutResponse).toBeOK()
  const loginResponse = await page.request.post('/api/v1/auth/login', {
    data: { identity_type: 'email', identity: account, password },
  })
  expect(loginResponse).toBeOK()
}
