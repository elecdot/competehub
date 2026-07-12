import type { Page } from '@playwright/test'

import { expect, test } from './fixtures/actors'

const competitionTitle = 'Browser AI Innovation Challenge 2026'

test.use({ actorName: 'editor' })

test('editor submits, distinct reviewer publishes, and student sees the edition', async ({
  actorPage,
}) => {
  await actorPage.goto('/admin')

  await actorPage.getByTestId('series-name').fill('Browser AI Innovation Challenge')
  await actorPage.getByTestId('create-series').click()

  await actorPage.getByTestId('edition-label').fill('2026')
  await actorPage.getByTestId('edition-title').fill(competitionTitle)
  await actorPage.getByTestId('category').fill('innovation')
  await actorPage.getByTestId('organizer').fill('Example University')
  await actorPage.getByTestId('source-name').fill('Example University Notice')
  await actorPage
    .getByTestId('source-url')
    .fill('https://example.edu/notices/browser-ai-2026')
  await actorPage.getByTestId('official-url').fill('https://example.org/browser-ai-2026')
  await actorPage.getByTestId('participant-forms').click()
  await actorPage
    .locator('.ant-select-dropdown:visible')
    .getByText('团队', { exact: true })
    .click()
  await actorPage.getByTestId('team-size').fill('2-5')
  await actorPage.getByTestId('majors').fill('Computer Science')
  await actorPage.getByTestId('grades').fill('Year 2, Year 3')
  await actorPage.getByTestId('node-time-0-0').fill('2026-08-01T08:00')
  await actorPage.getByTestId('node-time-0-1').fill('2026-08-15T23:59')
  await actorPage
    .getByTestId('summary')
    .fill('A complete source-backed browser publication candidate.')
  await actorPage.getByTestId('eligibility').fill('Enrolled undergraduate students.')
  await actorPage.getByTestId('add-tag').click()
  await actorPage.getByTestId('tag-code-0').fill('browser-ai')
  await actorPage.getByTestId('tag-name-0').fill('Browser AI')

  const createResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith('/api/v1/admin/competitions'),
  )
  await actorPage.getByTestId('save-revision').click()
  const createdWorkspace = await (await createResponsePromise).json()
  const editionId = createdWorkspace.data.id as number
  const revisionId = createdWorkspace.data.revision.id as number
  await expect(actorPage.getByText('draft · r1')).toBeVisible()
  await expect(actorPage.getByTestId('revision-completeness')).toContainText('发布完整度已满足')

  await actorPage.getByTestId('official-url').clear()
  await actorPage.getByTestId('participant-forms').click()
  await actorPage
    .locator('.ant-select-dropdown:visible')
    .getByText('团队', { exact: true })
    .click()
  await expect(actorPage.getByTestId('team-size')).toBeHidden()
  await actorPage.getByTestId('summary').fill('An edited source-backed browser publication candidate.')
  await actorPage.getByTestId('add-stage').click()
  await actorPage.getByTestId('stage-key-1').fill('submission')
  await actorPage.getByTestId('stage-type-1').fill('submission')
  await actorPage.getByTestId('stage-label-1').fill('Submission')
  await actorPage.getByTestId('node-key-1-0').fill('submission-note')
  await actorPage.getByTestId('node-time-1-0').fill('2026-08-20T23:59')
  await actorPage.getByTestId('node-description-1-0').fill('Submission instructions published')
  const updateResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'PATCH' &&
      response.url().endsWith(`/api/v1/admin/competition_revisions/${revisionId}`),
  )
  await actorPage.getByTestId('save-revision').click()
  const updateResponse = await updateResponsePromise
  expect(updateResponse.request().postDataJSON()).toMatchObject({
    official_url: null,
    participant_forms: ['individual'],
    team_size: null,
  })
  const storedRevisionResponse = await actorPage.request.get(
    `/api/v1/admin/competition_revisions/${revisionId}`,
  )
  expect(storedRevisionResponse).toBeOK()
  expect((await storedRevisionResponse.json()).data).toMatchObject({
    official_url: null,
    participant_forms: ['individual'],
    team_size: null,
  })
  await expect(actorPage.getByText('候选修订已更新')).toBeVisible()
  await expect(actorPage.getByTestId('stage-editor-1')).toBeVisible()

  await actorPage.reload()
  await expect(actorPage.getByTestId('edition-select')).toBeVisible()
  await expect(actorPage.getByText('draft · r1')).toBeVisible()
  await expect(actorPage.getByTestId('edition-title')).toHaveValue(competitionTitle)
  await expect(actorPage.getByTestId('official-url')).toHaveValue('')
  await expect(actorPage.getByTestId('team-size')).toBeHidden()
  await expect(actorPage.getByTestId('stage-editor-1')).toBeVisible()

  await actorPage
    .getByTestId('summary')
    .fill('A reloaded and continued source-backed browser publication candidate.')
  const reloadedUpdateResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'PATCH' &&
      response.url().endsWith(`/api/v1/admin/competition_revisions/${revisionId}`),
  )
  await actorPage.getByTestId('save-revision').click()
  await reloadedUpdateResponsePromise
  await expect(actorPage.getByText('候选修订已更新')).toBeVisible()

  await actorPage.getByTestId('submit-revision').click()
  await expect(actorPage.getByText('pending_review · r1')).toBeVisible()

  await actorPage.getByRole('tab', { name: '审核队列' }).click()
  await actorPage.getByRole('button', { name: new RegExp(competitionTitle) }).click()
  await expect(actorPage.getByTestId('review-diff')).toContainText('submission')
  await expect(actorPage.getByTestId('review-diff')).toContainText('submission-note')
  await expect(actorPage.getByTestId('review-impact')).toHaveText('publish')
  await expect(actorPage.getByTestId('self-review-warning')).toBeVisible()
  await expect(actorPage.getByTestId('approve-revision')).toBeDisabled()

  await switchActor(actorPage, 'reviewer.day1@example.edu', 'silver orchard compass cloud 59')
  await actorPage.reload()
  await actorPage.getByRole('tab', { name: '审核队列' }).click()
  await actorPage.getByRole('button', { name: new RegExp(competitionTitle) }).click()
  await actorPage.getByTestId('review-comment').fill('Source, scope, and chronology verified.')
  await actorPage.getByTestId('approve-revision').click()
  await expect(actorPage.getByText('暂无待审核修订')).toBeVisible()

  await switchActor(actorPage, 'student.day1@example.edu', 'violet harbor lantern orbit 47')
  await actorPage.goto('/competitions')
  const publicCard = actorPage
    .getByRole('article')
    .filter({ has: actorPage.getByRole('heading', { name: competitionTitle }) })
  await expect(publicCard).toBeVisible()
  await expect(publicCard).toContainText('2026')
  await expect(publicCard).toContainText('Browser AI')

  const publicDetailResponse = await actorPage.request.get(`/api/v1/competitions/${editionId}`)
  expect(publicDetailResponse).toBeOK()
  expect((await publicDetailResponse.json()).data).toMatchObject({
    official_url: null,
    participant_forms: ['individual'],
    team_size: null,
  })

  await actorPage.goto('/admin')
  await expect(actorPage.getByText('无权访问赛事发布工作台', { exact: true })).toBeVisible()
})

async function switchActor(page: Page, account: string, password: string) {
  const logoutResponse = await page.request.post('/api/v1/auth/logout')
  expect(logoutResponse).toBeOK()
  const loginResponse = await page.request.post('/api/v1/auth/login', {
    data: { identity_type: 'email', identity: account, password },
  })
  expect(loginResponse).toBeOK()
}
