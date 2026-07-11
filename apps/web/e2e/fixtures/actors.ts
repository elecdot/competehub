import {
  expect,
  test as base,
  type Page,
} from '@playwright/test'

export const actorNames = ['student', 'profileReady', 'editor', 'reviewer'] as const

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
  profileReady: {
    email: 'profile.student-day1@example.edu',
    password: 'green campus theorem delta 64',
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

export const pendingActor = {
  email: 'pending.day1@example.edu',
  password: 'amber bridge pending code 91',
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
  actorPage: async ({ page, actor, actorName }, use) => {
    await authenticateActorPage(page, actor, actorName)
    await use(page)
  },
})

async function authenticateActorPage(
  page: Page,
  actor: ActorDefinition,
  actorName: ActorName,
) {
  const loginResponse = await page.request.post('/api/v1/auth/login', {
    data: {
      identity_type: 'email',
      identifier: actor.email,
      password: actor.password,
    },
  })
  expect(loginResponse, `${actorName} login should succeed`).toBeOK()

  const currentUserResponse = await page.request.get('/api/v1/me')
  expect(currentUserResponse, `${actorName} cookie session should reach /me`).toBeOK()
  const currentUser = (await currentUserResponse.json()) as {
    data: { role: string }
  }
  expect(currentUser.data.role).toBe(actor.role)
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
