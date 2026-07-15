import type { Page } from '@playwright/test'

import { expect, test } from './fixtures/actors'

const offlineCompetitionId = 2002
const unpublishedCompetitionId = 2003

test.use({ actorName: 'student' })

test('student deletes an owned offline favorite through an authenticated browser request', async ({
  actorPage,
}) => {
  await actorPage.goto('/me')

  const result = await deleteOwnedRelation(
    actorPage,
    `/api/v1/competitions/${offlineCompetitionId}/favorite`,
  )

  expect(result.status).toBe(200)
  expect(result.body).toEqual({
    data: { competition_id: offlineCompetitionId, is_favorited: false },
    error: null,
  })
})

test('student deletes an owned unpublished subscription through an authenticated browser request', async ({
  actorPage,
}) => {
  await actorPage.goto('/me')

  const result = await deleteOwnedRelation(
    actorPage,
    `/api/v1/competitions/${unpublishedCompetitionId}/subscription`,
  )

  expect(result.status).toBe(200)
  expect(result.body).toEqual({
    data: {
      competition_id: unpublishedCompetitionId,
      status: 'cancelled',
      is_subscribed: false,
    },
    error: null,
  })
})

async function deleteOwnedRelation(page: Page, expectedPath: string) {
  const requestPromise = page.waitForRequest(
    (request) => request.method() === 'DELETE' && new URL(request.url()).pathname === expectedPath,
  )
  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'DELETE' &&
      new URL(response.url()).pathname === expectedPath,
  )
  const result = await page.evaluate(async (path) => {
    const response = await fetch(path, { method: 'DELETE', credentials: 'same-origin' })
    return { status: response.status, body: await response.json() }
  }, expectedPath)
  const [request, response] = await Promise.all([requestPromise, responsePromise])

  expect(request.method()).toBe('DELETE')
  expect(new URL(request.url()).pathname).toBe(expectedPath)
  expect(response.status()).toBe(200)
  return result
}
