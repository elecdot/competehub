import request from './request';

export function getCalendar() {
  return request.get('/reminders/calendar') as Promise<unknown>;
}

export function updateReminderSettings(payload: Record<string, unknown>) {
  return request.put('/reminders/settings', payload) as Promise<unknown>;
}
