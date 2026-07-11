import { actorNames, expect, test } from './fixtures/actors'

for (const actorName of actorNames) {
  test.describe(`${actorName} actor`, () => {
    test.use({ actorName })

    test('loads a nonblank browser path through a real cookie session', async ({ actorPage }) => {
      await actorPage.goto('/')

      expect(actorPage.video(), 'actorPage should inherit Playwright video recording').not.toBeNull()
      await expect(actorPage.locator('#main-content')).toBeVisible()
      await expect(actorPage.locator('body')).toContainText('CompeteHub')
      expect((await actorPage.locator('body').innerText()).trim().length).toBeGreaterThan(0)
    })
  })
}
