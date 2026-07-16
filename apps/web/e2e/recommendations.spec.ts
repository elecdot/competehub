import { expect, test } from './fixtures/actors'

function deferred() {
  let release!: () => void
  const promise = new Promise<void>((resolve) => {
    release = resolve
  })
  return { promise, release }
}

test.describe('recommendation modes', () => {
  test('serves useful anonymous recommendations without login', async ({ page }) => {
    await page.goto('/recommendations')

    await expect(page.getByRole('heading', { name: '推荐赛事' })).toBeVisible()
    await expect(page.getByText('通用推荐', { exact: true })).toBeVisible()
    await expect(page.getByText('当前无可用学生画像，展示通用可行动推荐。')).toBeVisible()
    await expect(page.getByRole('article')).toHaveCount(1)
    await expect(page.getByText('近期可行动的公开赛事')).toBeVisible()
  })

  test.describe('profile-ready student', () => {
    test.use({ actorName: 'profileReady' })

    test('shows traceable personalized reasons and current competition facts', async ({
      actorPage,
    }) => {
      const recommendationResponsePromise = actorPage.waitForResponse(
        (response) =>
          response.request().method() === 'GET' &&
          new URL(response.url()).pathname === '/api/v1/recommendations',
      )
      await actorPage.goto('/recommendations')
      const recommendationResponse = await recommendationResponsePromise
      expect(recommendationResponse.ok()).toBeTruthy()
      const recommendationPayload = await recommendationResponse.json()
      const ruleSetVersion = recommendationPayload.data.rule_set_version
      expect(ruleSetVersion).toEqual(expect.any(Number))

      await expect(actorPage.getByText('个性化推荐', { exact: true })).toBeVisible()
      await expect(actorPage.getByText(`规则集 v${ruleSetVersion}`)).toBeVisible()
      const card = actorPage.getByRole('article').filter({
        has: actorPage.getByRole('heading', {
          name: 'Seeded University Innovation Challenge 2025',
        }),
      })
      await expect(card).toBeVisible()
      await expect(card.getByText('推荐理由')).toBeVisible()
      await expect(card).toContainText('软件工程')
      await expect(card).toContainText('人工智能')
      await expect(card.getByText('报名开放')).toBeVisible()
      await expect(card.getByText('推荐分数')).toHaveCount(0)
      await expect(card.getByText('含金量评分')).toHaveCount(0)

      await card.getByRole('link', { name: '查看赛事详情' }).click()
      await expect(
        actorPage.getByRole('heading', { name: 'Seeded University Innovation Challenge 2025' }),
      ).toBeVisible()
    })

    test('shows explicit missing-configuration fallback', async ({ actorPage }) => {
      await actorPage.route('**/api/v1/recommendations', async (route) => {
        const response = await route.fetch()
        const payload = await response.json()
        payload.data.recommendation_mode = 'general'
        payload.data.rule_set_version = null
        payload.data.fallback_reason = 'no_active_rule_set'
        for (const item of payload.data.items) {
          item.reason_codes = ['general_fallback']
          item.reasons = ['按当前报名可行动性排序的公开赛事']
        }
        await route.fulfill({ response, json: payload })
      })

      await actorPage.goto('/recommendations')

      await expect(
        actorPage.getByText('推荐规则暂不可用，已切换为通用推荐。'),
      ).toBeVisible()
      await expect(actorPage.getByText('通用推荐', { exact: true })).toBeVisible()
    })
  })

  test.describe('incomplete student', () => {
    test.use({ actorName: 'recommendationIncomplete' })

    test('shows exact missing profile fields without personal-match claims', async ({
      actorPage,
    }) => {
      await actorPage.goto('/recommendations')

      await expect(actorPage.getByText('通用推荐', { exact: true })).toBeVisible()
      await expect(
        actorPage.getByText('画像尚未完整，当前展示通用推荐。'),
      ).toBeVisible()
      await expect(actorPage.getByText('待补充：学院、专业、年级、兴趣方向')).toBeVisible()
      await expect(actorPage.getByText(/与你的专业|适合你的年级|符合你的兴趣/)).toHaveCount(0)
    })
  })

  test.describe('authenticated non-student', () => {
    test.use({ actorName: 'adminNoRecommendation' })

    test('uses neutral general-fallback copy', async ({ actorPage }) => {
      await actorPage.goto('/recommendations')

      await expect(actorPage.getByText('通用推荐', { exact: true })).toBeVisible()
      await expect(
        actorPage.getByText('当前无可用学生画像，展示通用可行动推荐。'),
      ).toBeVisible()
      await expect(actorPage.getByText('当前未登录，展示通用可行动推荐。')).toHaveCount(0)
    })
  })
})

test.describe('recommendation state evidence', () => {
  test.use({ actorName: 'recommendationIncomplete', allowRecommendationRequestErrors: true })

  test('shows loading and empty states', async ({ actorPage }) => {
    const pending = deferred()
    await actorPage.route('**/api/v1/recommendations', async (route) => {
      await pending.promise
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            recommendation_mode: 'general',
            profile_status: 'incomplete',
            missing_fields: ['college', 'major', 'grade', 'interest_tags'],
            fallback_reason: 'profile_incomplete',
            rule_set_version: null,
            items: [],
          },
          error: null,
        }),
      })
    })

    await actorPage.goto('/recommendations')
    await expect(actorPage.getByRole('status')).toContainText('正在加载推荐赛事')
    pending.release()
    await expect(actorPage.getByText('暂无可推荐的公开赛事')).toBeVisible()
  })

  test('shows an actionable error state', async ({ actorPage }) => {
    await actorPage.route('**/api/v1/recommendations', async (route) => {
      await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' })
    })

    await actorPage.goto('/recommendations')

    await expect(actorPage.getByRole('alert')).toContainText('推荐赛事加载失败')
    await expect(actorPage.getByRole('link', { name: '浏览全部赛事' })).toBeVisible()
  })
})
