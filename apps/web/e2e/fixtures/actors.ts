import {
  expect,
  test as base,
  type Browser,
  type Page,
} from '@playwright/test'

export const actorNames = ['student', 'editor', 'reviewer'] as const

export type ActorName = (typeof actorNames)[number]

interface ActorDefinition {
  email: string
  password: string
  role: 'student' | 'admin'
}

const actors: Record<ActorName, ActorDefinition> = {
  student: {
    email: 'student.day1@example.edu',
    password: 'violet harbor lantern orbit 47',
    role: 'student',
  },
  editor: {
    email: 'admin.day1@example.edu',
    password: 'copper meadow signal river 82',
    role: 'admin',
  },
  reviewer: {
    email: 'reviewer.day1@example.edu',
    password: 'silver orchard compass cloud 59',
    role: 'admin',
  },
}

interface ActorFixtures {
  actor: ActorDefinition
  actorName: ActorName
  actorPage: Page
}

export const test = base.extend<ActorFixtures>({
  actorName: ['student', { option: true }],
  actor: async ({ actorName }, use) => {
    await use(actors[actorName])
  },
  page: async ({ page }, use) => {
    await usePageWithErrorGuard(page, use)
  },
  actorPage: async ({ baseURL, browser, actor, actorName }, use) => {
    const page = await createActorPage(browser, baseURL, actor, actorName)
    try {
      await usePageWithErrorGuard(page, use)
    } finally {
      await page.context().close()
    }
  },
})

async function createActorPage(
  browser: Browser,
  baseURL: string | undefined,
  actor: ActorDefinition,
  actorName: ActorName,
) {
  const context = await browser.newContext({ baseURL })
  try {
    const page = await context.newPage()

    // Keep the current tracer payload shape isolated here. Issue #34 updates this
    // helper to typed identities while preserving real login and cookie behavior.
    const loginResponse = await page.request.post('/api/v1/auth/login', {
      data: { account: actor.email, password: actor.password },
    })
    expect(loginResponse, `${actorName} login should succeed`).toBeOK()

    const currentUserResponse = await page.request.get('/api/v1/me')
    expect(currentUserResponse, `${actorName} cookie session should reach /me`).toBeOK()
    const currentUser = (await currentUserResponse.json()) as {
      data: { role: string }
    }
    expect(currentUser.data.role).toBe(actor.role)

    return page
  } catch (error) {
    await context.close()
    throw error
  }
}

async function usePageWithErrorGuard(
  page: Page,
  use: (page: Page) => Promise<void>,
) {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() === 'error') {
      errors.push(`console: ${message.text()}`)
    }
  })

  await use(page)
  expect(errors, 'uncaught page and console errors').toEqual([])
}

export { expect }
