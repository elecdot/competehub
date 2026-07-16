<script setup lang="ts">
import type {
  CalendarApi,
  CalendarOptions,
  DatesSetArg,
  EventInput,
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

import { fetchCalendar } from '@/api/client'
import { useCalendarViewStore } from '@/stores/calendar_view_store'
import type { CalendarItem, CalendarView } from '@/types/calendar'
import { formatNodeLabel } from '@/utils/competition'

const PRODUCT_TIME_ZONE = 'Asia/Shanghai'
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
  navLinks: true,
  dayMaxEvents: true,
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
}

function handleDatesSet(arg: DatesSetArg) {
  const view = FULL_CALENDAR_VIEWS[arg.view.type]
  if (!view) return
  viewStore.selectView(view)
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
    const events = payload.items.map(toFullCalendarEvent)
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
  const fullCalendarView = calendarRef.value?.getApi().view.type
  return (fullCalendarView && FULL_CALENDAR_VIEWS[fullCalendarView]) || viewStore.selectedView
}

function toFullCalendarEvent(item: CalendarItem): EventInput {
  const nodeLabel = item.description?.trim() || formatNodeLabel(item.node_type)
  return {
    id: `${item.competition_id}:${item.node_snapshot_id}`,
    title: `${item.competition_title} · ${nodeLabel}`,
    start: item.occurs_at,
    url: item.detail_url ?? undefined,
    extendedProps: { calendarItem: item },
  }
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
        <FullCalendar ref="calendarRef" :options="calendarOptions" />
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
}

@media (max-width: 640px) {
  .calendar-surface {
    padding: 12px;
  }

  :deep(.fc .fc-toolbar) {
    align-items: stretch;
    gap: 10px;
  }

  :deep(.fc .fc-toolbar-title) {
    font-size: 17px;
  }
}
</style>
