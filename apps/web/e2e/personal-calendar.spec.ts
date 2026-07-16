import type { Page } from '@playwright/test'

import { expect, test } from './fixtures/actors'

type CalendarView = 'month' | 'week' | 'list'
type CalendarBox = { x: number; y: number; width: number; height: number }

const CALENDAR_COMPETITION_ID = 2005
const CALENDAR_NODE_IDS = ['2501', '2502', '2503', '2504']
const LEGACY_REVISION_NODE_ID = '2511'
const OFFLINE_NODE_ID = '2601'
const VIEW_STORAGE_KEY = 'competehub.calendar.view'
const FIXED_BROWSER_NOW = new Date('2026-07-16T00:00:00+08:00')
const LONG_CALENDAR_TITLE = 'Seeded Calendar Challenge With A Long Responsive Title 2026'
const LONG_NODE_DESCRIPTION = 'Registration closes after a deliberately long responsive description'

interface CalendarResponse {
  data: {
    range: {
      from: string
      to: string
      view: CalendarView
      time_zone: 'Asia/Shanghai'
    }
    items: Array<{
      competition_id: number
      node_snapshot_id: number
      target_available: boolean
    }>
  }
  error: null
}

test.describe('personal calendar', () => {
  test.use({ actorName: 'calendarStudent' })

  test('renders seeded nodes across responsive month week and list views', async ({
    actorPage,
  }, testInfo) => {
    const mobile = testInfo.project.name === 'mobile-chromium'
    await actorPage.clock.setFixedTime(FIXED_BROWSER_NOW)
    await actorPage.goto('/')
    await actorPage.evaluate((key) => window.localStorage.removeItem(key), VIEW_STORAGE_KEY)

    const initialView: CalendarView = mobile ? 'list' : 'month'
    const initialResponse = waitForCalendarResponse(actorPage, initialView)
    await actorPage.goto('/me/calendar')
    const initialCalendarResponse = await initialResponse
    expect(initialCalendarResponse.ok()).toBe(true)
    const initialPayload = (await initialCalendarResponse.json()) as CalendarResponse

    expect(initialPayload.data.range.view).toBe(initialView)
    expect(initialPayload.data.range.time_zone).toBe('Asia/Shanghai')
    expect(calendarNodeIds(initialPayload)).toEqual(CALENDAR_NODE_IDS)
    await expectView(actorPage, initialView)
    const primaryEvent = actorPage.locator(`[data-calendar-node-id="${CALENDAR_NODE_IDS[0]}"]`)
    await expect(primaryEvent).toBeVisible()
    await expect(actorPage.locator(`[data-calendar-node-id="${LEGACY_REVISION_NODE_ID}"]`)).toHaveCount(0)
    await expect(primaryEvent.locator('[data-calendar-meta]')).toContainText('报名阶段')
    await expect(primaryEvent.locator('[data-calendar-meta]')).toContainText('报名配对·截止')
    await expect(primaryEvent.locator('[data-calendar-meta]')).toContainText('修订 2')
    await expect(primaryEvent.locator('.calendar-event-title')).toContainText(LONG_CALENDAR_TITLE)
    await expect(primaryEvent).toHaveAttribute('aria-label', new RegExp(LONG_CALENDAR_TITLE))
    if (mobile) {
      await expect(primaryEvent.locator('[data-calendar-meta]')).toBeVisible()
    } else {
      await expect(primaryEvent.locator('.calendar-event-node')).toContainText(
        LONG_NODE_DESCRIPTION,
      )
    }
    await expectCalendarLayout(actorPage)

    const intermediateView: CalendarView = 'week'
    await switchView(actorPage, intermediateView)
    expect(await actorPage.evaluate((key) => window.localStorage.getItem(key), VIEW_STORAGE_KEY)).toBe(
      intermediateView,
    )
    await expect(
      actorPage.locator(`[data-calendar-node-id="${CALENDAR_NODE_IDS[0]}"]`),
    ).toBeVisible()
    if (mobile) {
      await expect(primaryEvent.locator('[data-calendar-meta]')).toBeVisible()
    }
    await expectCalendarLayout(actorPage)

    const retainedView: CalendarView = mobile ? 'month' : 'list'
    const retainedPayload = await switchView(actorPage, retainedView)
    expect(await actorPage.evaluate((key) => window.localStorage.getItem(key), VIEW_STORAGE_KEY)).toBe(
      retainedView,
    )
    expect(calendarNodeIds(retainedPayload)).toEqual(CALENDAR_NODE_IDS)
    if (mobile) {
      await expect(primaryEvent.locator('[data-calendar-meta]')).toBeVisible()
    }
    await expectCalendarLayout(actorPage)

    const reloadResponse = waitForCalendarResponse(actorPage, retainedView)
    await actorPage.reload()
    expect((await reloadResponse).ok()).toBe(true)
    await expectView(actorPage, retainedView)

    let monthPayload = retainedPayload
    if (retainedView !== 'month') {
      monthPayload = await switchView(actorPage, 'month')
    }
    await expect(actorPage.locator('.fc-daygrid-day-number[href]')).toHaveCount(0)
    expect(
      monthPayload.data.items.some(
        (item) => item.node_snapshot_id === Number(OFFLINE_NODE_ID) && !item.target_available,
      ),
    ).toBe(true)
    await expectCalendarLayout(actorPage)

    const moreLink = actorPage.locator('.fc-daygrid-more-link')
    await expect(moreLink).toHaveText('+1 个节点')
    await moreLink.click()
    const popover = actorPage.locator('.fc-popover')
    await expect(popover).toBeVisible()

    const primary = popover.locator(`[data-calendar-node-id="${CALENDAR_NODE_IDS[0]}"]`)
    await expect(primary).toHaveAttribute(
      'aria-label',
      /重点节点.*最近节点.*报名配对·截止.*节点修订 2/,
    )
    await expect(popover.locator('[data-current-stage="true"]')).toHaveCount(1)
    await expect(
      popover.locator(`[data-calendar-node-id="${CALENDAR_NODE_IDS[3]}"]`),
    ).toHaveAttribute('aria-label', /比赛配对·开始/)
    if (!mobile) {
      await expect(popover.getByText('重点', { exact: true }).first()).toBeVisible()
      await expect(popover.getByText('当前阶段', { exact: true })).toBeVisible()
      await expect(popover.getByText('最近', { exact: true })).toBeVisible()
      await expect(popover.getByText('修订 2', { exact: true })).toBeVisible()
    }

    const unavailable = actorPage.locator(`[data-calendar-node-id="${OFFLINE_NODE_ID}"]`)
    await expect(unavailable).toHaveAttribute('aria-disabled', 'true')
    await expect(unavailable).not.toHaveAttribute('href', /.+/)
    await expect(unavailable).toHaveAttribute('aria-label', /已下架.*目标暂不可访问/)
    await expect(unavailable.locator('[data-calendar-meta]')).toContainText('已下架')
    await expect(unavailable.locator('[data-calendar-meta]')).toContainText('不可访问')
    if (mobile) await expect(unavailable.locator('[data-calendar-meta]')).toBeVisible()

    await actorPage.locator('.fc-popover-close').dispatchEvent('click')
    await expect(popover).toBeHidden()
    await actorPage
      .locator(`[data-calendar-node-id="${CALENDAR_NODE_IDS[0]}"]:visible`)
      .first()
      .click()
    await expect(actorPage).toHaveURL(`/competitions/${CALENDAR_COMPETITION_ID}`)
  })
})

function calendarNodeIds(payload: CalendarResponse) {
  return payload.data.items
    .filter((item) => item.competition_id === CALENDAR_COMPETITION_ID)
    .map((item) => String(item.node_snapshot_id))
}

async function switchView(page: Page, view: CalendarView): Promise<CalendarResponse> {
  const response = waitForCalendarResponse(page, view)
  await page.getByRole('button', { name: viewButtonName(view), exact: true }).click()
  const calendarResponse = await response
  expect(calendarResponse.ok()).toBe(true)
  const payload = (await calendarResponse.json()) as CalendarResponse
  await expectView(page, view)
  return payload
}

function waitForCalendarResponse(page: Page, view: CalendarView) {
  return page.waitForResponse((response) => {
    const url = new URL(response.url())
    return (
      response.request().method() === 'GET' &&
      url.pathname === '/api/v1/me/calendar' &&
      url.searchParams.get('view') === view
    )
  })
}

async function expectView(page: Page, view: CalendarView) {
  const selector = {
    month: '.fc-daygrid',
    week: '.fc-timegrid',
    list: '.fc-list',
  }[view]
  await expect(page.locator(selector)).toBeVisible()
}

function viewButtonName(view: CalendarView) {
  return { month: '月', week: '周', list: '列表' }[view]
}

async function expectCalendarLayout(page: Page) {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }))
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1)

  const regions = page.locator(
    '.calendar-page:visible, .calendar-surface:visible, .fc-toolbar:visible, .calendar-event-content:visible',
  )
  for (const region of await regions.all()) {
    const box = await region.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(-1)
    expect(box!.x + box!.width).toBeLessThanOrEqual(dimensions.viewport + 1)
    const scrollWidth = await region.evaluate((element) => element.scrollWidth)
    const clientWidth = await region.evaluate((element) => element.clientWidth)
    expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1)
  }

  const viewButtons = await Promise.all(
    (['month', 'week', 'list'] as CalendarView[]).map(async (view) => {
      const button = page.getByRole('button', { name: viewButtonName(view), exact: true })
      await expect(button).toBeVisible()
      return button
    }),
  )
  const boxes = await Promise.all(viewButtons.map((button) => button.boundingBox()))
  for (const box of boxes) {
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(-1)
    expect(box!.x + box!.width).toBeLessThanOrEqual(dimensions.viewport + 1)
  }
  for (let left = 0; left < boxes.length; left += 1) {
    for (let right = left + 1; right < boxes.length; right += 1) {
      expect(boxesOverlap(boxes[left]!, boxes[right]!)).toBe(false)
    }
  }
}

function boxesOverlap(left: CalendarBox, right: CalendarBox) {
  return (
    left.x < right.x + right.width &&
    left.x + left.width > right.x &&
    left.y < right.y + right.height &&
    left.y + left.height > right.y
  )
}
