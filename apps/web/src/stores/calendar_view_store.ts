import { defineStore } from 'pinia'

import type { CalendarView } from '@/types/calendar'

const VIEW_STORAGE_KEY = 'competehub.calendar.view'
const MOBILE_QUERY = '(max-width: 640px)'

function initialView(): CalendarView {
  if (typeof window === 'undefined') return 'month'
  try {
    const storedView = window.localStorage.getItem(VIEW_STORAGE_KEY)
    if (isCalendarView(storedView)) return storedView
  } catch {
    // Fall back to the viewport default when persistent storage is unavailable.
  }
  return window.matchMedia(MOBILE_QUERY).matches ? 'list' : 'month'
}

function isCalendarView(value: string | null): value is CalendarView {
  return value === 'month' || value === 'week' || value === 'list'
}

export const useCalendarViewStore = defineStore('calendarView', {
  state: () => ({ selectedView: initialView() }),
  actions: {
    selectView(view: CalendarView) {
      this.selectedView = view
      if (typeof window === 'undefined') return
      try {
        window.localStorage.setItem(VIEW_STORAGE_KEY, view)
      } catch {
        // View switching remains usable when private browsing blocks storage.
      }
    },
  },
})
