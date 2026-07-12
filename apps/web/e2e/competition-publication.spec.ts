import type { Page } from '@playwright/test'

import { expect, test } from './fixtures/actors'

test.use({ actorName: 'editor' })

test('editor submits, distinct reviewer publishes, and student sees the edition', async ({
  actorPage,
}, testInfo) => {
  test.setTimeout(90_000)
  const retrySuffix = `retry-${testInfo.retry}`
  const seriesName = `Browser AI Innovation Challenge ${retrySuffix}`
  const competitionTitle = `Browser AI Innovation Challenge 2026 ${retrySuffix}`
  const alternateCompetitionTitle = `Browser AI Innovation Challenge 2027 ${retrySuffix}`
  const sourceUrl = `https://example.edu/notices/browser-ai-2026-${retrySuffix}`
  const alternateSourceUrl = `https://example.edu/notices/browser-ai-2027-${retrySuffix}`
  const officialUrl = `https://example.org/browser-ai-2026-${retrySuffix}`
  const tagCode = `browser-ai-${retrySuffix}`

  await actorPage.goto('/admin')

  await actorPage.getByTestId('series-name').fill(seriesName)
  const seriesResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith('/api/v1/admin/competition_series'),
  )
  await actorPage.getByTestId('create-series').click()
  const createdSeries = await (await seriesResponsePromise).json()
  const seriesId = createdSeries.data.id as number

  await actorPage.getByTestId('new-edition').click()
  await expect(actorPage.getByTestId('edition-label')).toHaveValue('')
  await expect(actorPage.getByTestId('edition-title')).toHaveValue('')
  await expect(actorPage.getByTestId('stage-editor-0')).toBeVisible()
  await expect(actorPage.getByTestId('node-editor-0-0')).toBeVisible()
  await expect(actorPage.getByTestId('node-editor-0-1')).toBeVisible()

  await actorPage.getByTestId('edition-label').fill('2026')
  await actorPage.getByTestId('edition-title').fill(competitionTitle)
  await actorPage.getByTestId('category').fill('innovation')
  await actorPage.getByTestId('organizer').fill('Example University')
  await actorPage.getByTestId('source-name').fill('Example University Notice')
  await actorPage
    .getByTestId('source-url')
    .fill(sourceUrl)
  await actorPage.getByTestId('official-url').fill(officialUrl)
  await actorPage.getByTestId('stage-key-0').fill('registration')
  await actorPage.getByTestId('stage-type-0').fill('registration')
  await actorPage.getByTestId('stage-label-0').fill('Registration')
  await actorPage.getByTestId('node-key-0-0').fill('registration-open')
  await actorPage.getByTestId('node-description-0-0').fill('Registration opens')
  await actorPage.getByTestId('node-key-0-1').fill('registration-deadline')
  await actorPage.getByTestId('node-description-0-1').fill('Registration deadline')
  await actorPage.getByTestId('participant-forms').click()
  await actorPage
    .locator('.ant-select-dropdown:visible')
    .getByText('团队', { exact: true })
    .click()
  await actorPage.getByTestId('team-size').fill('2-5')
  await selectScope(actorPage, 'major-scope')
  await expect(actorPage.getByTestId('majors')).toBeEnabled()
  await actorPage.getByTestId('majors').fill('Computer Science')
  await selectScope(actorPage, 'grade-scope')
  await expect(actorPage.getByTestId('grades')).toBeEnabled()
  await actorPage.getByTestId('grades').fill('Year 2, Year 3')
  await actorPage.getByTestId('node-time-0-0').fill('2026-08-01T08:00')
  await actorPage.getByTestId('node-time-0-1').fill('2026-08-15T23:59')
  await actorPage
    .getByTestId('summary')
    .fill('A complete source-backed browser publication candidate.')
  await actorPage.getByTestId('eligibility').fill('Enrolled undergraduate students.')
  await actorPage.getByTestId('add-tag').click()
  await actorPage.getByTestId('tag-code-0').fill(tagCode)
  await actorPage.getByTestId('tag-name-0').fill('Browser AI')

  const createResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith('/api/v1/admin/competitions'),
  )
  await actorPage.getByTestId('save-revision').click()
  const createResponse = await createResponsePromise
  expect(createResponse.status()).toBe(201)
  expect(createResponse.request().postDataJSON()).toMatchObject({ series_id: seriesId })
  const createdWorkspace = await createResponse.json()
  const editionId = createdWorkspace.data.id as number
  const revisionId = createdWorkspace.data.revision.id as number
  await expect(actorPage.getByText('draft · r1')).toBeVisible()
  await expect(actorPage.getByTestId('revision-completeness')).toContainText('发布完整度已满足')

  await actorPage.getByTestId('new-edition').click()
  await expect(actorPage.getByTestId('edition-title')).toHaveValue('')
  await actorPage.getByTestId('edition-label').fill('2027')
  await actorPage.getByTestId('edition-title').fill(alternateCompetitionTitle)
  await actorPage.getByTestId('category').fill('innovation')
  await actorPage.getByTestId('organizer').fill('Example University')
  await actorPage.getByTestId('source-name').fill('Example University Notice')
  await actorPage.getByTestId('source-url').fill(alternateSourceUrl)
  await actorPage.getByTestId('summary').fill('A 2027 browser publication candidate.')
  await actorPage.getByTestId('eligibility').fill('Enrolled undergraduate students.')
  await actorPage.getByTestId('node-time-0-0').fill('2027-08-01T08:00')
  await actorPage.getByTestId('node-time-0-1').fill('2027-08-15T23:59')
  await expect(actorPage.getByTestId('majors')).toBeEnabled()
  await actorPage.getByTestId('majors').fill('Computer Science')
  await expect(actorPage.getByTestId('grades')).toBeEnabled()
  await actorPage.getByTestId('grades').fill('Year 2, Year 3')
  await expect(actorPage.getByTestId('category')).toHaveValue('innovation')
  await expect(actorPage.getByTestId('majors')).toHaveValue('Computer Science')
  await expect(actorPage.getByTestId('grades')).toHaveValue('Year 2, Year 3')
  await expect(actorPage.getByTestId('node-time-0-0')).toHaveValue('2027-08-01T08:00')
  await expect(actorPage.getByTestId('node-time-0-1')).toHaveValue('2027-08-15T23:59')
  const alternateCreateResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith('/api/v1/admin/competitions'),
  )
  await actorPage.getByTestId('save-revision').click()
  const alternateCreateResponse = await alternateCreateResponsePromise
  expect(alternateCreateResponse.status()).toBe(201)
  const alternateCreatedWorkspace = await alternateCreateResponse.json()
  expect(alternateCreatedWorkspace.data.id).toEqual(expect.any(Number))
  expect(alternateCreatedWorkspace.data.revision.id).toEqual(expect.any(Number))
  await selectEdition(actorPage, `2026 · ${competitionTitle}`)

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
  await expect(actorPage.getByText('候选修订已更新').last()).toBeVisible()
  await expect(actorPage.getByTestId('stage-editor-1')).toBeVisible()

  await actorPage.reload()
  await expect(actorPage.getByTestId('edition-select')).toBeVisible()
  await selectEdition(actorPage, `2026 · ${competitionTitle}`)
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
  await expect(actorPage.getByText('候选修订已更新').last()).toBeVisible()

  await actorPage.getByTestId('submit-revision').click()
  await expect(actorPage.getByText('pending_review · r1')).toBeVisible()

  await selectEdition(actorPage, `2027 · ${alternateCompetitionTitle}`)
  await expect(actorPage.getByTestId('edition-title')).toHaveValue(alternateCompetitionTitle)
  await expect(actorPage.getByText('draft · r1')).toBeVisible()
  await selectEdition(actorPage, `2026 · ${competitionTitle}`)
  await expect(actorPage.getByTestId('edition-title')).toHaveValue(competitionTitle)
  await expect(actorPage.getByText('pending_review · r1')).toBeVisible()
  await expect(actorPage.getByTestId('save-revision')).toBeDisabled()
  await expect(actorPage.getByTestId('submit-revision')).toBeDisabled()

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

  await switchActor(actorPage, 'admin.day1@example.edu', 'copper meadow signal river 82')
  await actorPage.goto('/admin')
  await selectEditionByTitle(actorPage, '2026', competitionTitle)
  await actorPage
    .getByTestId('successor-reason')
    .fill('Official source postponed the registration deadline.')
  const successorResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().endsWith(`/api/v1/admin/competitions/${editionId}/revisions`),
  )
  await actorPage.getByTestId('create-successor-revision').click()
  const successorResponse = await successorResponsePromise
  expect(successorResponse.ok()).toBe(true)
  const successorRevisionId = (await successorResponse.json()).data.id as number
  await expect(actorPage.getByText(/draft.*r2/)).toBeVisible()
  await actorPage.getByTestId('node-time-0-1').fill('2026-08-20T23:59')
  await actorPage.getByTestId('save-revision').click()
  await actorPage.getByTestId('submit-revision').click()
  await expect(actorPage.getByText(/pending_review.*r2/)).toBeVisible()

  const stillOldPublic = await actorPage.request.get(`/api/v1/competitions/${editionId}`)
  expect((await stillOldPublic.json()).data.revision_id).toBe(revisionId)

  await switchActor(actorPage, 'reviewer.day1@example.edu', 'silver orchard compass cloud 59')
  await actorPage.reload()
  await actorPage.getByRole('tab').nth(1).click()
  await actorPage.getByRole('button', { name: new RegExp(competitionTitle) }).click()
  await expect(actorPage.getByTestId('review-diff')).toContainText('registration-deadline')
  await actorPage.getByTestId('review-comment').fill('Updated deadline verified at source.')
  await actorPage.getByTestId('approve-revision').click()

  const switchedPublic = await actorPage.request.get(`/api/v1/competitions/${editionId}`)
  expect(switchedPublic).toBeOK()
  expect((await switchedPublic.json()).data).toMatchObject({
    revision_id: successorRevisionId,
    status: 'published',
  })

  await switchActor(actorPage, 'admin.day1@example.edu', 'copper meadow signal river 82')
  await actorPage.goto('/admin')
  await selectEditionByTitle(actorPage, '2026', competitionTitle)
  await actorPage.getByTestId('lifecycle-target').click()
  await actorPage
    .locator('.ant-select-dropdown:visible')
    .getByText('Emergency offline', { exact: true })
    .click()
  await actorPage.getByTestId('lifecycle-reason').fill('Official link ownership is unsafe.')
  const lifecycleResponsePromise = actorPage.waitForResponse(
    (response) =>
      response.request().method() === 'PATCH' &&
      response.url().endsWith(`/api/v1/admin/competitions/${editionId}/status`),
  )
  await actorPage.getByTestId('maintain-lifecycle').click()
  expect((await lifecycleResponsePromise).ok()).toBe(true)

  await switchActor(actorPage, 'student.day1@example.edu', 'violet harbor lantern orbit 47')
  const offlineDetail = await actorPage.request.get(`/api/v1/competitions/${editionId}`)
  expect(offlineDetail.status()).toBe(404)

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

async function selectEdition(page: Page, label: string) {
  await page.getByTestId('edition-select').click()
  await page.locator('.ant-select-dropdown:visible').getByText(label, { exact: true }).click()
}

async function selectScope(page: Page, testId: 'major-scope' | 'grade-scope') {
  await page.keyboard.press('Escape')
  await expect(page.locator('.ant-select-dropdown:visible')).toHaveCount(0)
  const select = page.getByTestId(testId)
  await select.locator('.ant-select-selector').click()
  const dropdown = page.locator('.ant-select-dropdown:visible')
  await expect(dropdown).toBeVisible()
  const selectedOption = dropdown
    .locator('.ant-select-item-option-content', { hasText: '指定' })
    .locator('..')
  await expect(selectedOption).toBeVisible()
  await selectedOption.click()
  await expect(select.locator('.ant-select-selection-item')).toHaveText('指定')
}

async function selectEditionByTitle(page: Page, editionLabel: string, title: string) {
  await page.getByTestId('edition-select').click()
  await page
    .locator('.ant-select-dropdown:visible .ant-select-item-option')
    .filter({ hasText: editionLabel })
    .filter({ hasText: title })
    .click()
}
