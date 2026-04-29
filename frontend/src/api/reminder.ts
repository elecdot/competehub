import request from './request';
import type { NotificationItem } from './types';

export function getCalendar() {
  return request.get('/reminders/calendar') as Promise<unknown>;
}

export function updateReminderSettings(payload: Record<string, unknown>) {
  return request.put('/reminders/settings', payload) as Promise<unknown>;
}

export function getNotifications() {
  return request.get('/reminders/notifications') as Promise<{ items: NotificationItem[]; unread: number }>;
}

export function markNotificationRead(id: number) {
  return request.put(`/reminders/notifications/${id}/read`) as Promise<unknown>;
}

export function markAllNotificationsRead() {
  return request.put('/reminders/notifications/read-all') as Promise<unknown>;
}
