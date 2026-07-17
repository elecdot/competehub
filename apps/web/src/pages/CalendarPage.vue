<script setup lang="ts">
import type {
  CalendarApi,
  CalendarOptions,
  DatesSetArg,
  EventApi,
  EventClickArg,
  EventInput,
  EventMountArg,
  EventSourceFuncArg,
} from '@fullcalendar/core'
import zhCnLocale from '@fullcalendar/core/locales/zh-cn'
import dayGridPlugin from '@fullcalendar/daygrid'
import listPlugin from '@fullcalendar/list'
import luxonPlugin from '@fullcalendar/luxon3'
import timeGridPlugin from '@fullcalendar/timegrid'
import FullCalendar from '@fullcalendar/vue3'
import { Alert as AAlert, Button as AButton, Empty as AEmpty, Spin as ASpin } from 'ant-design-vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchCalendar } from '@/api/client'
import { useCalendarViewStore } from '@/stores/calendar_view_store'
import type { CalendarItem, CalendarView } from '@/types/calendar'
import { formatNodeLabel } from '@/utils/competition'

const PRODUCT_TIME_ZONE = 'Asia/Shanghai'
const LIFECYCLE_LABELS: Record<string, string> = {
  cancelled: '已取消',
  archived: '已归档',
  expired: '已过期',
  offline: '已下架',
}
const CALENDAR_VIEWS: Record<CalendarView, string> = {
  month: 'dayGridMonth',
  week: 'timeGridWeek',
  list: 'listWeek',
}
const FULL_CALENDAR_VIEWS: Record<string, CalendarView> = {
  dayGridMonth: 'month',
  timeGridWeek: 'week',
  listWeek: 'list',
}

type FullCalendarRef = {
  getApi: () => CalendarApi
}

const viewStore = useCalendarViewStore()
const router = useRouter()
const initialView = viewStore.selectedView
const calendarRef = ref<FullCalendarRef | null>(null)
const loading = ref(false)
const loadedOnce = ref(false)
const visibleItemCount = ref(0)
const errorMessage = ref('')
let requestSequence = 0

const calendarOptions: CalendarOptions = {
  plugins: [dayGridPlugin, timeGridPlugin, listPlugin, luxonPlugin],
  initialView: CALENDAR_VIEWS[initialView],
  locale: zhCnLocale,
  timeZone: PRODUCT_TIME_ZONE,
  firstDay: 1,
  height: 'auto',
  nowIndicator: true,
  navLinks: false,
  dayMaxEvents: 3,
  eventDisplay: 'block',
  eventOrderStrict: true,
  eventOrder: (left, right) =>
    compareCalendarItems(
      calendarItemFromEvent(left as EventApi),
      calendarItemFromEvent(right as EventApi),
    ),
  moreLinkContent: (arg) => `+${arg.num} 个节点`,
  displayEventEnd: false,
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,listWeek',
  },
  buttonText: {
    today: '今天',
    month: '月',
    week: '周',
    list: '列表',
  },
  eventTimeFormat: {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  },
  datesSet: handleDatesSet,
  events: loadEvents,
  eventClick: handleEventClick,
  eventDidMount: enhanceEventAccessibility,
}

function handleDatesSet(arg: DatesSetArg) {
  const view = FULL_CALENDAR_VIEWS[arg.view.type]
  if (!view) return
  const viewChanged = viewStore.selectedView !== view
  viewStore.selectView(view)
  if (viewChanged) {
    calendarRef.value?.getApi().refetchEvents()
  }
}

async function loadEvents(
  fetchInfo: EventSourceFuncArg,
  successCallback: (events: EventInput[]) => void,
) {
  const requestId = ++requestSequence
  loading.value = true
  errorMessage.value = ''

  try {
    const payload = await fetchCalendar({
      from: toProductDate(fetchInfo.start),
      to: toProductDate(new Date(fetchInfo.end.getTime() - 1)),
      view: activeCalendarView(),
    })
    const events = toFullCalendarEvents(payload.items)
    successCallback(events)
    if (requestId === requestSequence) {
      visibleItemCount.value = payload.items.length
      loadedOnce.value = true
    }
  } catch {
    successCallback([])
    if (requestId === requestSequence) {
      visibleItemCount.value = 0
      loadedOnce.value = true
      errorMessage.value = '个人赛事日历暂时无法加载，请稍后再试。'
    }
  } finally {
    if (requestId === requestSequence) loading.value = false
  }
}

function activeCalendarView(): CalendarView {
  try {
    const fullCalendarView = calendarRef.value?.getApi().view.type
    if (fullCalendarView && FULL_CALENDAR_VIEWS[fullCalendarView]) {
      return FULL_CALENDAR_VIEWS[fullCalendarView]
    }
  } catch {
    // FullCalendar requests its first event range before the component ref is ready.
  }
  return viewStore.selectedView
}

function toFullCalendarEvents(items: CalendarItem[]): EventInput[] {
  const nearestUpcomingSnapshotId = nearestUpcomingNode(items)?.node_snapshot_id
  return items.map((item) =>
    toFullCalendarEvent(item, item.node_snapshot_id === nearestUpcomingSnapshotId),
  )
}

function toFullCalendarEvent(item: CalendarItem, isNearestUpcoming: boolean): EventInput {
  const nodeLabel = item.description?.trim() || formatNodeLabel(item.node_type)
  return {
    id: `${item.competition_id}:${item.node_snapshot_id}`,
    title: `${item.competition_title} · ${nodeLabel}`,
    start: item.occurs_at,
    url: item.detail_url ?? undefined,
    classNames: [
      'calendar-event',
      `calendar-event--${item.prominence}`,
      ...(item.is_current_stage ? ['calendar-event--current-stage'] : []),
      ...(isNearestUpcoming ? ['calendar-event--nearest'] : []),
      ...(item.pair_kind ? ['calendar-event--paired'] : []),
      ...(!item.target_available ? ['calendar-event--unavailable'] : []),
    ],
    extendedProps: { calendarItem: item, isNearestUpcoming },
  }
}

function nearestUpcomingNode(items: CalendarItem[]): CalendarItem | null {
  const now = Date.now()
  return (
    items
      .filter((item) => Date.parse(item.occurs_at) >= now)
      .sort((left, right) => Date.parse(left.occurs_at) - Date.parse(right.occurs_at))[0] ?? null
  )
}

function compareCalendarItems(left: CalendarItem, right: CalendarItem): number {
  return (
    nullableStageOrder(left.stage_order) - nullableStageOrder(right.stage_order) ||
    Date.parse(left.occurs_at) - Date.parse(right.occurs_at) ||
    prominenceOrder(left.prominence) - prominenceOrder(right.prominence) ||
    left.node_snapshot_id - right.node_snapshot_id
  )
}

function nullableStageOrder(value: number | null): number {
  return value ?? Number.MAX_SAFE_INTEGER
}

function prominenceOrder(value: CalendarItem['prominence']): number {
  return value === 'primary' ? 0 : 1
}

function calendarItemFromEvent(event: EventApi): CalendarItem {
  return event.extendedProps.calendarItem as CalendarItem
}

function isNearestUpcomingEvent(event: EventApi): boolean {
  return event.extendedProps.isNearestUpcoming === true
}

function handleEventClick(arg: EventClickArg) {
  arg.jsEvent.preventDefault()
  const item = calendarItemFromEvent(arg.event)
  if (item.target_available && item.detail_url) {
    void router.push(item.detail_url)
  }
}

function enhanceEventAccessibility(arg: EventMountArg) {
  const item = calendarItemFromEvent(arg.event)
  const label = eventAccessibleLabel(arg.event)
  arg.el.setAttribute('aria-label', label)
  arg.el.setAttribute('title', label)
  arg.el.dataset.calendarNodeId = String(item.node_snapshot_id)
  arg.el.dataset.prominence = item.prominence
  arg.el.dataset.currentStage = String(item.is_current_stage)
  arg.el.dataset.targetAvailable = String(item.target_available)
  arg.el.dataset.nodeRevision = String(item.node_revision)
  if (!item.target_available) {
    arg.el.removeAttribute('href')
    arg.el.setAttribute('aria-disabled', 'true')
  }
}

function eventAccessibleLabel(event: EventApi): string {
  const item = calendarItemFromEvent(event)
  return [
    item.competition_title,
    item.description?.trim() || formatNodeLabel(item.node_type),
    item.stage_label,
    item.prominence === 'primary' ? '重点节点' : '普通节点',
    item.is_current_stage ? '当前阶段' : null,
    isNearestUpcomingEvent(event) ? '最近节点' : null,
    formatPairLabel(item),
    `节点修订 ${item.node_revision}`,
    lifecycleLabel(item),
    item.target_available ? null : '目标暂不可访问',
  ]
    .filter((value): value is string => Boolean(value))
    .join('，')
}

function formatPairLabel(item: CalendarItem): string | null {
  if (item.pair_kind === 'registration') {
    return item.pair_role === 'start' ? '报名配对·开始' : '报名配对·截止'
  }
  if (item.pair_kind === 'competition') {
    return item.pair_role === 'start' ? '比赛配对·开始' : '比赛配对·结束'
  }
  return null
}

function lifecycleLabel(item: CalendarItem): string | null {
  return LIFECYCLE_LABELS[item.lifecycle_status] ?? null
}

function eventMetadataLabels(event: EventApi): string[] {
  const item = calendarItemFromEvent(event)
  return [
    item.stage_label ? `阶段：${item.stage_label}` : null,
    formatPairLabel(item),
    `修订 ${item.node_revision}`,
    lifecycleLabel(item),
    item.target_available ? null : '不可访问',
  ].filter((value): value is string => Boolean(value))
}

function toProductDate(value: Date): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: PRODUCT_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(value)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

function reloadCalendar() {
  calendarRef.value?.getApi().refetchEvents()
}
</script>

<template>
  <section class="calendar-page">
    <header>
      <h1 class="page-title">个人赛事日历</h1>
      <p class="page-description">
        按上海时间查看已订阅赛事的报名、提交和比赛节点。
      </p>
    </header>

    <AAlert
      v-if="errorMessage"
      type="error"
      show-icon
      :message="errorMessage"
      role="alert"
    >
      <template #action>
        <AButton size="small" @click="reloadCalendar">重新加载</AButton>
      </template>
    </AAlert>

    <ASpin :spinning="loading" tip="正在加载日历…">
      <div class="calendar-surface" :aria-busy="loading">
        <FullCalendar ref="calendarRef" :options="calendarOptions">
          <template #eventContent="{ event, timeText }">
            <div class="calendar-event-content">
              <time v-if="timeText" class="calendar-event-time">{{ timeText }}</time>
              <strong class="calendar-event-title">{{
                calendarItemFromEvent(event).competition_title
              }}</strong>
              <span class="calendar-event-node">{{
                calendarItemFromEvent(event).description?.trim() ||
                formatNodeLabel(calendarItemFromEvent(event).node_type)
              }}</span>
              <span class="calendar-event-meta" data-calendar-meta aria-hidden="true">
                <span
                  v-for="label in eventMetadataLabels(event)"
                  :key="label"
                  class="calendar-event-meta-token"
                >
                  {{ label }}
                </span>
              </span>
              <span class="calendar-event-badges" aria-hidden="true">
                <span
                  v-if="calendarItemFromEvent(event).prominence === 'primary'"
                  class="calendar-event-badge"
                >
                  重点
                </span>
                <span
                  v-if="calendarItemFromEvent(event).is_current_stage"
                  class="calendar-event-badge"
                >
                  当前阶段
                </span>
                <span v-if="isNearestUpcomingEvent(event)" class="calendar-event-badge">
                  最近
                </span>
                <span
                  v-if="formatPairLabel(calendarItemFromEvent(event))"
                  class="calendar-event-badge"
                >
                  {{ formatPairLabel(calendarItemFromEvent(event)) }}
                </span>
                <span
                  v-if="lifecycleLabel(calendarItemFromEvent(event))"
                  class="calendar-event-badge"
                >
                  {{ lifecycleLabel(calendarItemFromEvent(event)) }}
                </span>
                <span
                  v-if="!calendarItemFromEvent(event).target_available"
                  class="calendar-event-badge"
                >
                  不可访问
                </span>
                <span
                  v-if="calendarItemFromEvent(event).node_revision > 1"
                  class="calendar-event-badge"
                >
                  修订 {{ calendarItemFromEvent(event).node_revision }}
                </span>
              </span>
            </div>
          </template>
        </FullCalendar>
      </div>
    </ASpin>

    <AEmpty
      v-if="loadedOnce && !loading && !errorMessage && visibleItemCount === 0"
      class="calendar-empty"
      description="当前日期范围内暂无已订阅赛事节点"
    />
  </section>
</template>

<style scoped>
.calendar-page {
  display: grid;
  gap: 20px;
}

.calendar-surface {
  background: #ffffff;
  border: 1px solid #dde2e7;
  border-radius: 8px;
  min-width: 0;
  padding: 20px;
}

.calendar-empty {
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 24px;
}

:deep(.fc) {
  --fc-border-color: #d9e0e7;
  --fc-button-active-bg-color: #145c42;
  --fc-button-active-border-color: #145c42;
  --fc-button-bg-color: #176b4d;
  --fc-button-border-color: #176b4d;
  --fc-button-hover-bg-color: #145c42;
  --fc-button-hover-border-color: #145c42;
  --fc-event-bg-color: #176b4d;
  --fc-event-border-color: #176b4d;
  --fc-page-bg-color: #ffffff;
  --fc-today-bg-color: rgb(23 107 77 / 8%);
  color: #1f2937;
}

:deep(.fc .fc-toolbar-title) {
  font-size: 20px;
  overflow-wrap: anywhere;
  text-align: center;
}

:deep(.fc .fc-daygrid-event),
:deep(.fc .fc-timegrid-event),
:deep(.fc .fc-list-event-title a) {
  white-space: normal;
}

:deep(.fc .calendar-event--secondary) {
  --fc-event-bg-color: #37637a;
  --fc-event-border-color: #37637a;
}

:deep(.fc .calendar-event--current-stage) {
  box-shadow: inset 4px 0 #f7c948;
}

:deep(.fc .calendar-event--nearest) {
  outline: 2px solid #f7c948;
  outline-offset: 1px;
}

:deep(.fc .calendar-event--unavailable) {
  --fc-event-bg-color: #eef2f6;
  --fc-event-border-color: #64748b;
  --fc-event-text-color: #334155;
  color: #334155;
  cursor: not-allowed;
}

.calendar-event-content {
  display: grid;
  gap: 2px;
  min-width: 0;
  padding: 2px;
}

.calendar-event-time {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}

.calendar-event-title,
.calendar-event-node {
  overflow-wrap: anywhere;
}

.calendar-event-title {
  font-size: 12px;
  line-height: 1.3;
}

.calendar-event-node {
  font-size: 11px;
  line-height: 1.35;
}

.calendar-event-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 2px;
}

.calendar-event-meta {
  display: none;
}

.calendar-event-badge {
  background: rgb(255 255 255 / 20%);
  border: 1px solid currentColor;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.2;
  padding: 1px 4px;
}

:deep(.fc .calendar-event--unavailable .calendar-event-badge) {
  background: #ffffff;
}

:deep(.fc .fc-daygrid-more-link) {
  color: #145c42;
  font-weight: 700;
}

:deep(.fc .fc-popover) {
  max-width: min(360px, calc(100vw - 32px));
}

@media (max-width: 640px) {
  .calendar-surface {
    padding: 12px;
  }

  :deep(.fc .fc-toolbar) {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  :deep(.fc .fc-toolbar-chunk) {
    display: flex;
    justify-content: center;
    max-width: 100%;
  }

  :deep(.fc .fc-button-group) {
    flex-wrap: wrap;
    justify-content: center;
  }

  :deep(.fc .fc-button) {
    min-height: 36px;
  }

  :deep(.fc .fc-daygrid-event .calendar-event-content),
  :deep(.fc .fc-timegrid-event .calendar-event-content) {
    display: block;
    overflow: hidden;
    padding: 1px;
  }

  :deep(.fc .fc-daygrid-event .calendar-event-time),
  :deep(.fc .fc-daygrid-event .calendar-event-title),
  :deep(.fc .fc-timegrid-event .calendar-event-time),
  :deep(.fc .fc-timegrid-event .calendar-event-title) {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :deep(.fc .fc-daygrid-event .calendar-event-node),
  :deep(.fc .fc-daygrid-event .calendar-event-badges),
  :deep(.fc .fc-timegrid-event .calendar-event-node),
  :deep(.fc .fc-timegrid-event .calendar-event-badges) {
    display: none;
  }

  :deep(.fc .fc-daygrid-event .calendar-event-meta),
  :deep(.fc .fc-timegrid-event .calendar-event-meta),
  :deep(.fc .fc-list-event .calendar-event-meta) {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    margin-top: 2px;
    max-width: 100%;
  }

  .calendar-event-meta-token {
    border: 1px solid currentColor;
    border-radius: 3px;
    font-size: 9px;
    line-height: 1.2;
    max-width: 100%;
    overflow-wrap: anywhere;
    padding: 1px 3px;
  }

  :deep(.fc .fc-toolbar-title) {
    font-size: 17px;
  }
}
</style>
