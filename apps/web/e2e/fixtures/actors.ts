import {
  expect,
  test as base,
  type Page,
} from '@playwright/test'

export const actorNames = [
  'student',
  'profileReady',
  'editor',
  'reviewer',
  'adminNoRecommendation',
] as const

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
  adminNoRecommendation: {
    email: 'admin.no-recommendation@example.edu',
    password: 'granite garden ordinary admin 28',
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
  allowLoginUnauthorizedConsoleError: boolean
  allowOutboundTrackingConsoleError: boolean
  allowProfileValidationConsoleError: boolean
}

export const test = base.extend<ActorFixtures>({
  actorName: ['student', { option: true }],
  allowLoginUnauthorizedConsoleError: [false, { option: true }],
  allowOutboundTrackingConsoleError: [false, { option: true }],
  allowProfileValidationConsoleError: [false, { option: true }],
  actor: async ({ actorName }, use) => {
    await use(actors[actorName])
  },
  page: async (
    {
      page,
      allowLoginUnauthorizedConsoleError,
      allowOutboundTrackingConsoleError,
      allowProfileValidationConsoleError,
    },
    use,
  ) => {
    await usePageWithErrorGuard(
      page,
      use,
      allowLoginUnauthorizedConsoleError,
      allowOutboundTrackingConsoleError,
      allowProfileValidationConsoleError,
    )
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
  allowLoginUnauthorizedConsoleError: boolean,
  allowOutboundTrackingConsoleError: boolean,
  allowProfileValidationConsoleError: boolean,
) {
  const errors: string[] = []
  let expectedHttpErrorResponses = 0
  let httpConsoleErrors = 0
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('response', (response) => {
    const request = response.request()
    const pathname = new URL(response.url()).pathname
    const isCurrentUserProbe =
      response.status() === 401 && request.method() === 'GET' && pathname === '/api/v1/me'
    const isExpectedLoginFailure =
      allowLoginUnauthorizedConsoleError &&
      response.status() === 401 &&
      request.method() === 'POST' &&
      pathname === '/api/v1/auth/login'
    const isExpectedProfileValidation =
      allowProfileValidationConsoleError &&
      response.status() === 400 &&
      request.method() === 'PATCH' &&
      pathname === '/api/v1/me/profile'
    const isExpectedOutboundTrackingFailure =
      allowOutboundTrackingConsoleError &&
      response.status() === 500 &&
      request.method() === 'POST' &&
      /^\/api\/v1\/competitions\/\d+\/outbound_clicks$/.test(pathname)
    if (
      isCurrentUserProbe ||
      isExpectedLoginFailure ||
      isExpectedOutboundTrackingFailure ||
      isExpectedProfileValidation
    ) {
      expectedHttpErrorResponses += 1
    } else if (response.status() === 400 || response.status() === 401) {
      errors.push(`response: unexpected ${response.status()} from ${request.method()} ${pathname}`)
    }
  })
  page.on('console', (message) => {
    if (message.type() !== 'error') {
      return
    }
    if (
      message.text().includes('status of 401') ||
      message.text().includes('status of 400') ||
      (allowOutboundTrackingConsoleError && message.text().includes('status of 500'))
    ) {
      httpConsoleErrors += 1
    } else {
      errors.push(`console: ${message.text()}`)
    }
  })

  await use(page)
  if (httpConsoleErrors > expectedHttpErrorResponses) {
    errors.push(
      `console: observed ${httpConsoleErrors} HTTP resource errors for ` +
        `${expectedHttpErrorResponses} expected responses`,
    )
  }
  expect(errors, 'uncaught page and console errors').toEqual([])
}

export { expect }
